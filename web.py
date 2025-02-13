from bbo import generate_bbo_triples
from bpmn import generate_raw_bpmn
from flask import request, send_file, Response
from helpers import error, query
from sparql_queries import generate_file_uri_select_query
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
        triples_per_subject = generate_bbo_triples(
            physical_visio_file_path, virtual_visio_file_uri
        )
        insert_triple_chunks(triples_per_subject)
    except Exception as e:
        print(e)
        return error("Something went wrong during process steps extraction.", 500)

    return triples_per_subject


def insert_triple_chunks(triple_chunks, max_triples_per_insert=100):
    index = 0
    triples_to_insert = []

    while index < len(triple_chunks):
        if (
            len(triples_to_insert) == 0
            or len(triples_to_insert) + len(triple_chunks[index])
            <= max_triples_per_insert
        ):
            triples_to_insert.extend(triple_chunks[index])

        index += 1

        if (
            index >= len(triple_chunks)
            or len(triples_to_insert) + len(triple_chunks[index])
            >= max_triples_per_insert
        ):
            print(triples_to_insert)
            print("########################")
            # triples_insert_query = generate_triples_insert_query(triples_to_insert)
            # update(triples_insert_query)
            triples_to_insert = []
