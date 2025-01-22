from string import Template
from escape_helpers import sparql_escape_uri

def generate_file_uri_select_query(virtual_file_uuid):
  return Template("""
    PREFIX mu: <http://mu.semte.ch/vocabularies/core/>
    PREFIX nfo: <http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#>
    PREFIX nie: <http://www.semanticdesktop.org/ontologies/2007/01/19/nie#>
    PREFIX dbpedia: <http://dbpedia.org/ontology/>

    SELECT *
    WHERE {
      ?virtualFileUri mu:uuid $virtual_file_uuid ;
        nfo:fileName ?virtualFileName ;
        dbpedia:fileExtension ?fileExtension .

      ?physicalFileUri nie:dataSource ?virtualFileUri .
    }
  """).substitute(virtual_file_uuid=sparql_escape_uri(virtual_file_uuid))