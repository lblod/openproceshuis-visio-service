from flask import request, jsonify, send_file
from helpers import error, query, update, generate_uuid
from sparql_queries import (
    generate_file_uri_select_query,
    generate_bpmn_file_insert_query,
)
from vsdx import VisioFile
from bpmn_tools.flow import Task, Flow, Process
from bpmn_tools.notation import Definitions
from bpmn_tools.diagrams import Plane, Diagram
from bpmn_tools.collaboration import Collaboration, Participant
from bpmn_tools.layout import graphviz
from bpmn_tools import util
from pathlib import Path
import os
import subprocess
import tempfile

STORAGE_FOLDER_PATH = "/share/"
FILE_URI_PREFIX = "http://mu.semte.ch/services/file-service/files"


@app.route("/<virtual_visio_file_uuid>", methods=["GET"])
def convert_visio_to_file(virtual_visio_file_uuid):
    virtual_visio_file_uuid = request.args.get("id")
    if not virtual_visio_file_uuid:
        return error("No file id provided", 400)

    visio_file_uri_query = generate_file_uri_select_query(virtual_visio_file_uuid)
    visio_file_uri_result = query(visio_file_uri_query)
    visio_file_uri_bindings = visio_file_uri_result["results"]["bindings"]
    if not visio_file_uri_bindings:
        return error("Not Found", 404)

    visio_file_extension = visio_file_uri_bindings[0]["fileExtension"]["value"]
    if not visio_file_extension == "vsdx":
        return error("Unsupported file type, exected .vsdx file.", 415)

    physical_visio_file_uri = visio_file_uri_bindings[0]["physicalFileUri"]["value"]
    physical_visio_file_path = physical_visio_file_uri.replace(
        "share://", STORAGE_FOLDER_PATH
    )
    if not os.path.exists(physical_visio_file_path):
        return error("Could not find file in path.", 500)

    target_extension = request.args.get("target-extension", "pdf").lower()
    if target_extension not in ["pdf"]:
        return error(f"Unsupported format: {target_extension}", 400)

    virtual_visio_file_name = visio_file_uri_bindings[0]["virtualFileName"]["value"]
    target_file_name = (
        f"{os.path.splitext(virtual_visio_file_name)[0]}.{target_extension}"
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        try:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    target_extension,
                    "--outdir",
                    temporary_directory,
                    physical_visio_file_path,
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            return error(f"Conversion failed: {e.stderr.decode()}", 500)

        original_file_name = os.path.splitext(
            os.path.basename(physical_visio_file_path)
        )[0]
        converted_file_path = os.path.join(
            temporary_directory, f"{original_file_name}.{target_extension}"
        )

        if not os.path.exists(converted_file_path):
            return error("Conversion failed.", 500)

        return send_file(
            converted_file_path,
            as_attachment=True,
            download_name=target_file_name,
        )


@app.route("/", methods=["POST"])
def convert_visio_to_bpmn():
    virtual_visio_file_uuid = request.args.get("id")
    if not virtual_visio_file_uuid:
        return error("No file id provided", 400)

    visio_file_uri_query = generate_file_uri_select_query(virtual_visio_file_uuid)
    visio_file_uri_result = query(visio_file_uri_query)
    visio_file_uri_bindings = visio_file_uri_result["results"]["bindings"]
    if not visio_file_uri_bindings:
        return error("Not Found", 404)

    virtual_visio_file_name = visio_file_uri_bindings[0]["virtualFileName"]["value"]
    virtual_visio_file_uri = visio_file_uri_bindings[0]["virtualFileUri"]["value"]

    physical_visio_file_uri = visio_file_uri_bindings[0]["physicalFileUri"]["value"]
    physical_visio_file_path = physical_visio_file_uri.replace(
        "share://", STORAGE_FOLDER_PATH
    )

    visio_file_extension = visio_file_uri_bindings[0]["fileExtension"]["value"]
    if not visio_file_extension == "vsdx":
        return error("Unsupported file type, exected .vsdx file.", 415)

    if not os.path.exists(physical_visio_file_path):
        return error("Could not find file in path.", 500)

    try:
        bpmn_raw = generate_raw_bpmn(physical_visio_file_path)
    except Exception as e:
        print(e)
        return error("Something went wrong during conversion", 500)

    virtual_bpmn_file_uuid = generate_uuid()
    virtual_bpmn_file_name = f"{os.path.splitext(virtual_visio_file_name)[0]}.bpmn"
    virtual_bpmn_file_uri = f"{FILE_URI_PREFIX}/{virtual_bpmn_file_uuid}"

    physical_bpmn_file_uuid = generate_uuid()
    physical_bpmn_file_name = f"{physical_bpmn_file_uuid}.bpmn"
    physical_bpmn_file_uri = f"share://{physical_bpmn_file_name}"
    physical_bpmn_file_path = physical_bpmn_file_uri.replace(
        "share://", STORAGE_FOLDER_PATH
    )

    Path(physical_bpmn_file_path).write_text(bpmn_raw)

    bpmn_file_insert_query = generate_bpmn_file_insert_query(
        virtual_bpmn_file_uuid,
        virtual_bpmn_file_name,
        virtual_bpmn_file_uri,
        physical_bpmn_file_uuid,
        physical_bpmn_file_name,
        physical_bpmn_file_uri,
        os.path.getsize(physical_bpmn_file_path),
        virtual_visio_file_uri,
    )
    update(bpmn_file_insert_query)

    return jsonify(
        {
            "message": "Visio file successfully converted to BPMN",
            "visio-file-id": virtual_visio_file_uuid,
            "bpmn-file-id": virtual_bpmn_file_uuid,
        }
    ), 201


def generate_raw_bpmn(physical_visio_file_path):
    # PAGES

    visio = VisioFile(physical_visio_file_path)
    page = visio.get_page(0)  # TODO: loop over pages

    # TASKS

    tasks = {}

    for shape in page.child_shapes:  # TODO: also consider deeper nested shapes
        # 'Shape' shapes are 'help' elements in Visio --> of no use in BPMN
        if shape.shape_type == "Shape":
            continue

        tasks[shape.ID] = Task(shape.text.strip(), id=f"task_{shape.ID}")

    # FLOWS

    flows = {}

    for connector in page.connects:
        task_id = connector.xml.attrib.get("ToSheet")

        # Some connectors are 'help' elements in Visio --> of no use in BPMN
        if task_id not in tasks:
            continue

        flow_id = connector.xml.attrib.get("FromSheet")
        flow_type = connector.xml.attrib.get("FromCell")

        if flow_id not in flows:
            flows[flow_id] = {}

        if flow_type == "BeginX":
            flows[flow_id]["source_task_id"] = task_id
        elif flow_type == "EndX":
            flows[flow_id]["target_task_id"] = task_id

        # Create flow object when both source and target are known
        if "source_task_id" in flows[flow_id] and "target_task_id" in flows[flow_id]:
            source_task_id = flows[flow_id]["source_task_id"]
            target_task_id = flows[flow_id]["target_task_id"]

            source_task = tasks[source_task_id]
            target_task = tasks[target_task_id]

            flows[flow_id] = Flow(
                source_task, target_task, id=f"flow_{flow_id}"
            )  # TODO: set flow name

    # PROCESS

    process = Process()
    process.extend(tasks.values())
    process.extend(flows.values())

    # COLLABORATION

    participant = Participant(process=process)  # TODO: fetch from Visio
    collaboration = Collaboration()  # TODO: fetch from Visio
    collaboration.append(participant)

    # DIAGRAM

    plane = Plane(element=collaboration)
    diagram = Diagram(plane=plane)

    # DEFINITIONS

    definitions = Definitions()
    definitions.append(process)
    definitions.append(collaboration)
    definitions.append(diagram)

    # BPMN

    graphviz.layout(definitions)
    return util.model2xml(definitions)
