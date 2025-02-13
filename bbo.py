import re
from helpers import generate_uuid
from visio import extract_visio_tasks_flows


BASE_URI = "http://data.lblod.info/"


def generate_bbo_task(_, label):
    task_uri = BASE_URI + generate_uuid()

    label = re.sub(r"\s+", " ", label)

    task = [
        f"<{task_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#Task> .",
        f"<{task_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#Activity> .",
        f"<{task_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#FlowNode> .",
        f"<{task_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#FlowElement> .",
        f'<{task_uri}> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#name> "{label}" .',
    ]

    return task_uri, task


def generate_bbo_flow(_, label, source_task_id, target_task_id, tasks):
    flow_uri = BASE_URI + generate_uuid()

    source_task_uri = tasks[source_task_id][0]
    target_task_uri = tasks[target_task_id][0]

    flow = [
        f"<{flow_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#SequenceFlow> .",
        f"<{flow_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#FlowElement> .",
        f"<{flow_uri}> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#has_sourceRef> <{source_task_uri}> .",
        f"<{flow_uri}> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#has_targetRef> <{target_task_uri}> .",
        f'<{flow_uri}> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#name> "{label}" .',
    ]

    return flow_uri, flow


def generate_bbo_triples(physical_visio_file_path, virtual_visio_file_uri):
    triples_per_subject = []

    # PROCESS

    process_uri = BASE_URI + generate_uuid()

    process = [
        f"<{process_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#Process> .",
        f"<{process_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#FlowElementsContainer> .",
        f"<{process_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#CallableElement> .",
        f"<{process_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.irit.fr/recherches/MELODI/ontologies/BBO#RootElement> .",
        f"<{process_uri}> <http://www.w3.org/ns/prov#wasDerivedFrom> <{virtual_visio_file_uri}> .",
    ]

    triples_per_subject.append(process)

    # TASKS & FLOWS

    tasks, flows = extract_visio_tasks_flows(
        physical_visio_file_path,
        generate_task_fn=generate_bbo_task,
        generate_flow_fn=generate_bbo_flow,
    )

    for subject, triples in list(tasks.values()) + list(flows.values()):
        triples.append(
            f"<{subject}> <https://www.teamingai-project.eu/belongsToProcess> <{process_uri}> ."
        )
        triples_per_subject.append(triples)

    return triples_per_subject
