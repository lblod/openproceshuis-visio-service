from visio import extract_visio_tasks_flows
from bpmn_tools.flow import Task, Flow, Process
from bpmn_tools.notation import Definitions
from bpmn_tools.diagrams import Plane, Diagram
from bpmn_tools.collaboration import Collaboration, Participant
from bpmn_tools.layout import graphviz
from bpmn_tools import util


def generate_bpmn_task(id, label):
    return Task(label, id=f"task_{id}")


def generate_bpmn_flow(id, label, source_task_id, target_task_id, tasks):
    source_task = tasks[source_task_id]
    target_task = tasks[target_task_id]
    return Flow(source_task, target_task, label, id=f"flow_{id}")


def generate_raw_bpmn(physical_visio_file_path):
    # TASKS & FLOWS

    tasks, flows = extract_visio_tasks_flows(
        physical_visio_file_path,
        generate_task_fn=generate_bpmn_task,
        generate_flow_fn=generate_bpmn_flow,
    )

    # PROCESS

    process = Process()
    process.extend(tasks.values())
    process.extend(flows.values())

    # COLLABORATION

    participant = Participant(process=process)
    collaboration = Collaboration()
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
