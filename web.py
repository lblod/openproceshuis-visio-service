from flask import request
from helpers import error, query
from sparql_queries import generate_file_uri_select_query
import os

STORAGE_FOLDER_PATH = "/share/"

@app.route("/", methods=["POST"])
def convert_visio_to_bpmn():
    virtual_file_uuid = request.args.get('id')
    if not virtual_file_uuid:
        return error('No file id provided', 400)
    
    file_uri_query = generate_file_uri_select_query(virtual_file_uuid)
    file_uri_result = query(file_uri_query)
    file_uri_bindings = file_uri_result['results']['bindings']
    if not file_uri_bindings:
        return error("Not Found", 404)
    virtual_file_uri = file_uri_bindings[0]['virtualFileUri']['value']
    virtual_file_name = file_uri_bindings[0]['virtualFileName']['value']
    physical_file_uri = file_uri_bindings[0]['physicalFileUri']['value']
    file_extension = file_uri_bindings[0]['fileExtension']['value']

    if not file_extension == 'vsdx':
        return error("Unsupported file type, exected .vsdx file.", 415)
    
    physical_file_path = physical_file_uri.replace("share://", STORAGE_FOLDER_PATH)
    if not os.path.exists(physical_file_path):
        return error("Could not find file in path. Check if the physical file is available on the server and if this service has the right mountpoint.", 500)

    return virtual_file_name