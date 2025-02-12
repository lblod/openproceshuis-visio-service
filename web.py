from bpmn import generate_raw_bpmn
from flask import request, jsonify, send_file, Response
from helpers import error, query, update, generate_uuid
from sparql_queries import (
    generate_file_uri_select_query,
    generate_bpmn_file_insert_query,
)
from pathlib import Path
import os
import subprocess
import tempfile

STORAGE_FOLDER_PATH = "/share/"
FILE_URI_PREFIX = "http://mu.semte.ch/services/file-service/files"


@app.route("/convert", methods=["GET"])
def convert_visio():
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

    target_extension = request.args.get("extension", "pdf").lower()
    if target_extension not in ["pdf", "bpmn"]:
        return error(f"Unsupported format: {target_extension}", 400)

    virtual_visio_file_name = visio_file_uri_bindings[0]["virtualFileName"]["value"]
    target_file_name = (
        f"{os.path.splitext(virtual_visio_file_name)[0]}.{target_extension}"
    )

    if target_extension == "pdf":
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

    elif target_extension == "bpmn":
        try:
            raw_bpmn = generate_raw_bpmn(physical_visio_file_path)
        except Exception as e:
            return error(f"BPMN conversion failed: {str(e)}", 500)

        return Response(
            raw_bpmn,
            mimetype="application/xml",
            headers={"Content-Disposition": f"attachment; filename={target_file_name}"},
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
