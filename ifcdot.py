#!/usr/bin/python3

import ifcopenshell
import ifcopenshell.util.element
import sys

# Copyright (C) 2023
# Bruno Postle <bruno@postle.net>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.


def write_dot(ifc_file, path_dot, interest=set()):
    """Create a GraphViz .dot file from an ifcopenshell file

    Command-line usage:

        ifcdot.py input.ifc graph.dot
        neato -Tsvg graph.dot > graph.svg

    Python usage:

        import ifcopenshell
        from ifcdot import write_dot
        ifc_file = ifcopenshell.open("/path/to/input.ifc")
        write_dot(ifc_file, "/path/to/graph.dot")

    The write_dot() function will render a graph with all IfcObject entities
    unless a subset of relevant entities is provided as an 'interest' parameter.
    write_dot() also returns a superset of entities that the 'interest' set are
    connected-to, so the following will show a graph containing a single entity #1234:

        new_interest = write_dot(ifc_file, "/path/to/graph.dot", interest={1234})

    Running the output as input will expand this graph to all Object entities
    that are connected-to #1234:

        write_dot(ifc_file, "/path/to/graph.dot", interest=new_interest)

    etc..
    """

    ifc_objects = {}
    new_interest = interest.copy()

    dot = open(path_dot, "w")
    dot.write("strict graph G {\n")
    dot.write("graph [overlap=false,splines=true,rankdir=LR];\n")

    for ifc_object in ifc_file.by_type("IfcObject"):
        if ifc_object.is_a("IfcVirtualElement"):
            continue

        ifc_objects[ifc_object.id()] = (
            "#" + str(ifc_object.id()) + "=" + str(ifc_object.is_a())
        )

        if interest and not ifc_object.id() in interest:
            continue

        if ifc_object.is_a("IfcGroup"):
            fill = "#ff99ff"
        elif ifc_object.is_a("IfcSpatialElement"):
            fill = "#ff99cc"
        elif ifc_object.is_a("IfcElementAssembly"):
            fill = "#ccff99"
        elif ifc_object.is_a("IfcOpeningElement"):
            fill = "#cc99ff"
        elif ifc_object.is_a("IfcDoor") or ifc_object.is_a("IfcWindow"):
            fill = "#99ccff"
        elif ifc_object.is_a("IfcElement"):
            fill = "#9999ff"
        elif ifc_object.is_a("IfcStructuralItem"):
            fill = "#99ff99"
        else:
            fill = "#ff9999"

        dot.write(
            '"'
            + ifc_objects[ifc_object.id()]
            + '" [color="'
            + fill
            + '",style=filled];\n'
        )

    for ifc_rel in ifc_file.by_type("IfcRelationship"):

        relating_object = None
        related_objects = []
        weight = "1"
        style = "solid"

        if ifc_rel.is_a("IfcRelAggregates"):
            relating_object = ifc_rel.RelatingObject
            related_objects = ifc_rel.RelatedObjects
            weight = "9"
        if ifc_rel.is_a("IfcRelNests"):
            relating_object = ifc_rel.RelatingObject
            related_objects = ifc_rel.RelatedObjects
            weight = "9"
        if ifc_rel.is_a("IfcRelAssignsToGroup"):
            relating_object = ifc_rel.RelatingGroup
            related_objects = ifc_rel.RelatedObjects
        if ifc_rel.is_a("IfcRelConnectsElements"):
            relating_object = ifc_rel.RelatingElement
            related_objects = [ifc_rel.RelatedElement]
            weight = "9"
            style = "dashed"
        if ifc_rel.is_a("IfcRelConnectsStructuralMember"):
            relating_object = ifc_rel.RelatingStructuralMember
            related_objects = [ifc_rel.RelatedStructuralConnection]
        if ifc_rel.is_a("IfcRelContainedInSpatialStructure"):
            relating_object = ifc_rel.RelatingStructure
            related_objects = ifc_rel.RelatedElements
        if ifc_rel.is_a("IfcRelFillsElement"):
            relating_object = ifc_rel.RelatingOpeningElement
            related_objects = [ifc_rel.RelatedBuildingElement]
            weight = "9"
        if ifc_rel.is_a("IfcRelVoidsElement"):
            relating_object = ifc_rel.RelatingBuildingElement
            related_objects = [ifc_rel.RelatedOpeningElement]
            weight = "9"
        if ifc_rel.is_a("IfcRelSpaceBoundary"):
            relating_object = ifc_rel.RelatingSpace
            related_objects = [ifc_rel.RelatedBuildingElement]
            weight = "9"
            style = "dotted"

        for related_object in related_objects:
            if (
                relating_object.id() in ifc_objects
                and related_object.id() in ifc_objects
            ):

                if interest:
                    if (
                        not relating_object.id() in interest
                        and not related_object.id() in interest
                    ):
                        continue
                    if (
                        relating_object.id() in interest
                        and not related_object.id() in interest
                    ):
                        new_interest.add(related_object.id())
                        continue
                    if (
                        related_object.id() in interest
                        and not relating_object.id() in interest
                    ):
                        new_interest.add(relating_object.id())
                        continue

                dot.write(
                    '"'
                    + ifc_objects[relating_object.id()]
                    + '"--"'
                    + ifc_objects[related_object.id()]
                    + '" ['
                    # + 'label="'
                    # + str(ifc_rel.is_a())
                    # + '" '
                    + "weight="
                    + weight
                    + ",style="
                    + style
                    + "];\n"
                )

    for ifc_object in ifc_file.by_type("IfcSite"):
        cluster(dot, ifc_object, ifc_objects, interest)

    dot.write("}\n")
    dot.close()
    return new_interest


def cluster(dot, ifc_object, ifc_objects, interest=set()):
    if ifc_object.is_a("IfcVirtualElement"):
        return
    if interest and not ifc_object.id() in interest:
        return

    children = ifcopenshell.util.element.get_decomposition(ifc_object)
    if children:
        dot.write("subgraph id_" + str(ifc_object.id()) + " {\n")
        dot.write("cluster=true;\n")
        dot.write('"' + ifc_objects[ifc_object.id()] + '";\n')

        for child in children:
            if child.is_a("IfcVirtualElement"):
                continue
            if interest and not child.id() in interest:
                continue
            dot.write('"' + ifc_objects[child.id()] + '";\n')
            cluster(dot, child, ifc_objects, interest=interest)
        dot.write("}\n")


if __name__ == "__main__":
    if not len(sys.argv) == 3:
        print("Usage: " + sys.argv[0] + " input.ifc graph.dot")
    else:
        path_ifc = sys.argv[1]
        path_dot = sys.argv[2]
        ifc_file = ifcopenshell.open(path_ifc)
        write_dot(ifc_file, path_dot)
