from vsdx import VisioFile
import os
import shutil


def extract_visio_tasks_flows(
    physical_visio_file_path, generate_task_fn, generate_flow_fn
):
    try:
        # PAGES

        visio = VisioFile(physical_visio_file_path)
        page = visio.get_page(0)  # TODO: loop over pages

        # TASKS

        tasks = {}

        for shape in page.child_shapes:  # TODO: also consider deeper nested shapes
            # 'Shape' shapes are 'help' elements in Visio --> of no use in BPMN
            if shape.shape_type == "Shape":
                continue

            label = shape.text.strip() if shape.text is not None else ""
            tasks[shape.ID] = generate_task_fn(shape.ID, label)

        # FLOWS

        flows_temp = {}
        flows = {}

        for connector in page.connects:
            task_id = connector.xml.attrib.get("ToSheet")

            # Some connectors are 'help' elements in Visio --> of no use in BPMN
            if task_id not in tasks:
                continue

            flow_id = connector.xml.attrib.get("FromSheet")
            flow_type = connector.xml.attrib.get("FromCell")

            if flow_id not in flows_temp:
                flows_temp[flow_id] = {}

            if flow_type == "BeginX":
                flows_temp[flow_id]["source_task_id"] = task_id
            elif flow_type == "EndX":
                flows_temp[flow_id]["target_task_id"] = task_id

            # Create flow object when both source and target are known
            if (
                "source_task_id" in flows_temp[flow_id]
                and "target_task_id" in flows_temp[flow_id]
            ):
                source_task_id = flows_temp[flow_id]["source_task_id"]
                target_task_id = flows_temp[flow_id]["target_task_id"]

                flow_shape = page.find_shape_by_id(flow_id)
                label = flow_shape.text.strip() if flow_shape.text is not None else ""

                flows[flow_id] = generate_flow_fn(
                    flow_id, label, source_task_id, target_task_id, tasks
                )

        return tasks, flows

    finally:
        helper_folder = os.path.splitext(physical_visio_file_path)[0]
        if os.path.isdir(helper_folder):
            shutil.rmtree(helper_folder)
