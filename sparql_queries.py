from datetime import datetime, timezone
from escape_helpers import (
    sparql_escape_uri,
    sparql_escape_string,
    sparql_escape_int,
    sparql_escape_datetime,
)


def generate_file_uri_select_query(virtual_file_uuid):
    return f"""
    PREFIX mu: <http://mu.semte.ch/vocabularies/core/>
    PREFIX nfo: <http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#>
    PREFIX nie: <http://www.semanticdesktop.org/ontologies/2007/01/19/nie#>
    PREFIX dbpedia: <http://dbpedia.org/ontology/>

    SELECT *
    WHERE {{
      ?virtualFileUri mu:uuid {sparql_escape_string(virtual_file_uuid)} ;
        nfo:fileName ?virtualFileName ;
        dbpedia:fileExtension ?fileExtension .

      ?physicalFileUri nie:dataSource ?virtualFileUri .
    }}
    """


def generate_bpmn_file_insert_query(
    virtual_file_uuid,
    virtual_file_name,
    virtual_file_uri,
    physical_file_uuid,
    physical_file_name,
    physical_file_uri,
    file_size,
    visio_file_uri,
):
    file_format = "text/xml; charset=utf-8"
    file_extension = "bpmn"
    now = datetime.now(timezone.utc)

    return f"""
    PREFIX nfo: <http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#>
    PREFIX dbpedia: <http://dbpedia.org/ontology/>
    PREFIX mu: <http://mu.semte.ch/vocabularies/core/>
    PREFIX dc: <http://purl.org/dc/terms/>
    PREFIX nie: <http://www.semanticdesktop.org/ontologies/2007/01/19/nie#>
    PREFIX prov: <http://www.w3.org/ns/prov#>

    INSERT DATA {{
      {sparql_escape_uri(virtual_file_uri)} a nfo:FileDataObject ;
          nfo:fileName {sparql_escape_string(virtual_file_name)} ;
          mu:uuid {sparql_escape_string(virtual_file_uuid)} ;
          dc:format {sparql_escape_string(file_format)} ;
          nfo:fileSize {sparql_escape_int(file_size)} ;
          dbpedia:fileExtension {sparql_escape_string(file_extension)} ;
          dc:created {sparql_escape_datetime(now)} ;
          dc:modified {sparql_escape_datetime(now)} ;
          prov:wasDerivedFrom {sparql_escape_uri(visio_file_uri)} .

      {sparql_escape_uri(physical_file_uri)} a nfo:FileDataObject ;
          nie:dataSource {sparql_escape_uri(virtual_file_uri)} ;
          nfo:fileName {sparql_escape_string(physical_file_name)} ;
          mu:uuid {sparql_escape_string(physical_file_uuid)} ;
          dc:format {sparql_escape_string(file_format)} ;
          nfo:fileSize {sparql_escape_int(file_size)} ;
          dbpedia:fileExtension {sparql_escape_string(file_extension)} ;
          dc:created {sparql_escape_datetime(now)} ;
          dc:modified {sparql_escape_datetime(now)} .
    }}
    """
