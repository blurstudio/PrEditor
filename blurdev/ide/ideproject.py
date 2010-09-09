##
# 	\namespace	blurdev.ide.ideproject
#
# 	\remarks	Stores information about a project
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from blurdev.enum import enum

ProjectType = enum('Application', 'Custom', 'Library', 'Tool', 'LegacyTool')


class IdeProject:
    projects = {}

    Command = {'.ui': ('c:/blur/common/designer.exe', '', 'c:/blur/common')}

    def __init__(self, projectType):
        self._name = ''
        self._path = ''
        self._icon = ''
        self._projectType = projectType

    def icon(self):
        return self._icon

    def name(self):
        return self._name

    def path(self):
        return self._path

    def projectType(self):
        return self._projectType

    def setName(self, name):
        self._name = name

    def setIcon(self, icon):
        self._icon = icon

    def setPath(self, path):
        self._path = path

    @staticmethod
    def projectsByType(projectType):
        output = []

        # tools use the environment system
        if projectType in (ProjectType.Tool, ProjectType.LegacyTool):
            from blurdev.tools import ToolsEnvironment

            tools = ToolsEnvironment.activeEnvironment().index().tools()
            tools.sort(lambda x, y: cmp(x.displayName(), y.displayName()))

            legacy = ProjectType.LegacyTool == projectType

            for tool in tools:
                if tool.isLegacy() == legacy:
                    output.append(IdeProject.fromTool(tool))

        # all other types use registration
        else:
            output = IdeProject.projects.get(projectType, [])

        return output

    @staticmethod
    def register(project):
        if not project.projectType() in IdeProject.projects:
            IdeProject.projects[project.projectType()] = [project]
        else:
            IdeProject.projects[project.projectType()].append(project)
            IdeProject.projects[project.projectType()].sort(
                lambda x, y: cmp(x.name(), y.name())
            )

    @staticmethod
    def fromTool(tool):
        if tool.isLegacy():
            ptype = ProjectType.LegacyTool
        else:
            ptype = ProjectType.Tool

        proj = IdeProject(ptype)
        proj.setName(tool.displayName())
        proj.setPath(tool.path())
        proj.setIcon(tool.icon())
        return proj

    @staticmethod
    def fromXml(xml):
        for child in xml.children():
            '<project name="Trax" type="Application" loc="c:/blur/trax" icon="c:/blur/trax/icon.png"/>'
            proj = IdeProject(ProjectType.value(child.attribute('type')))
            proj.setName(child.attribute('name'))
            proj.setPath(child.attribute('loc'))
            proj.setIcon(child.attribute('icon'))
            IdeProject.register(proj)

    @staticmethod
    def toXml(parent):
        node = parent.addNode('projects')
        for grp in IdeProject.projects.values():
            for proj in grp:
                elem = node.addNode('project')
                elem.setAttribute('name', elem.name())
                elem.setAttribute('type', ProjectType.key(elem.projectType()))
                elem.setAttribute('loc', elem.path())
                elem.setAttribute('icon', elem.icon())

    @staticmethod
    def load(filename):
        from blurdev.XML import XMLDocument

        doc = XMLDocument()
        if doc.load(filename):
            IdeProject.fromXml(doc.root())


import os.path

IdeProject.load(os.path.split(__file__)[0] + '/projects.xml')
