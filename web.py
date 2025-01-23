from flask import request, send_file
from helpers import error, query
from sparql_queries import generate_file_uri_select_query
from vsdx import VisioFile
from bpmn_tools.flow import Task, Flow, Process
from bpmn_tools.notation import Definitions
from bpmn_tools.diagrams import Plane, Diagram
from bpmn_tools.collaboration import Collaboration, Participant
from bpmn_tools.layout import graphviz
from bpmn_tools import util
import tempfile
import os

STORAGE_FOLDER_PATH = "/share/"


@app.route("/", methods=["POST"])
def convert_visio_to_bpmn():
    virtual_file_uuid = request.args.get("id")
    if not virtual_file_uuid:
        return error("No file id provided", 400)

    file_uri_query = generate_file_uri_select_query(virtual_file_uuid)
    file_uri_result = query(file_uri_query)
    file_uri_bindings = file_uri_result["results"]["bindings"]
    if not file_uri_bindings:
        return error("Not Found", 404)
    virtual_file_uri = file_uri_bindings[0]["virtualFileUri"]["value"]
    virtual_file_name = file_uri_bindings[0]["virtualFileName"]["value"]
    physical_file_uri = file_uri_bindings[0]["physicalFileUri"]["value"]
    file_extension = file_uri_bindings[0]["fileExtension"]["value"]

    if not file_extension == "vsdx":
        return error("Unsupported file type, exected .vsdx file.", 415)

    physical_file_path = physical_file_uri.replace("share://", STORAGE_FOLDER_PATH)
    if not os.path.exists(physical_file_path):
        return error(
            "Could not find file in path. Check if the physical file is available on the server and if this service has the right mountpoint.",
            500,
        )

    # PAGES

    visio = VisioFile(physical_file_path)
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
    bpmn_raw = util.model2xml(definitions)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bpmn") as bpmn_file:
        bpmn_file.write(bpmn_raw.encode("utf-8"))
        bpmn_file_path = bpmn_file.name

    virtual_file_name, _ = os.path.splitext(virtual_file_name)

    try:
        return send_file(
            bpmn_file_path,
            as_attachment=True,
            download_name=f"{virtual_file_name}.bpmn",
            mimetype="application/xml",
        )
    finally:
        os.remove(bpmn_file_path)
