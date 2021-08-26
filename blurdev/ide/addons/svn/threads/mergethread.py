##
# 	\namespace	blurdev.ide.addons.svn.threads
#
# 	\remarks	Contains various threads to be run during the SVN process
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/25/11
#

from __future__ import absolute_import
import pysvn

from blurdev.ide.addons.svn.threads import ActionThread


class MergeThread(ActionThread):
    def __init__(self):
        super(MergeThread, self).__init__()

        # define common merging properties
        self._pegRevision = pysvn.Revision(pysvn.opt_revision_kind.head)
        self._depth = pysvn.depth.empty
        self._noticeAncestry = False
        self._force = False
        self._dryRun = False
        self._recordOnly = False
        self._additionalOptions = []

    def additionalOptions(self):
        return self._additionalOptions

    def depth(self):
        return self._depth

    def dryRun(self):
        return self._dryRun

    def force(self):
        return self._force

    def noticeAncestry(self):
        return self._noticeAncestry

    def pegRevision(self):
        return self._pegRevision

    def recordOnly(self):
        return self._recordOnly

    def setAdditionalOptions(self, options):
        self._additionalOptions = options

    def setDepth(self, depth):
        self._depth = depth

    def setDryRun(self, state):
        self._dryRun = state

    def setForce(self, state):
        self._force = state

    def setNoticeAncestry(self, state):
        self._noticeAncestry = state

    def setPegRevision(self, revision):
        self._pegRevision = revision

    def setRecordOnly(self, state):
        self._recordOnly = state


class MergeRangesThread(MergeThread):
    def __init__(self):
        super(MergeRangesThread, self).__init__()

        self.setTitle('Merge Ranges')

        self._url = ''
        self._ranges = []
        self._targetPath = ''

    def ranges(self):
        return self._ranges

    def runClient(self, client):
        """
            \remarks	checkin the information to the client
            \param		client		<pysvn.Client>
        """
        self.notify({'action': 'Merge from', 'path': self.url()})
        self.notify({'action': 'Merge to', 'path': self.targetPath()})
        self.notify({'action': 'Depth', 'path': str(self.depth())})
        client.merge_peg2(
            self.url(),
            self.ranges(),
            self.pegRevision(),
            self.targetPath(),
            depth=self.depth(),
            notice_ancestry=self.noticeAncestry(),
            force=self.force(),
            dry_run=self.dryRun(),
            record_only=self.recordOnly(),
            merge_options=self.additionalOptions(),
        )

    def setRanges(self, ranges):
        if type(ranges) == str:
            results = ranges.split(',')
            ranges = []
            for result in results:
                result = result.strip()

                # parse out valid revision ranges (the start should be 1- the inputed
                # revision number for the range)
                try:
                    if '-' in result:
                        start, end = result.split('-')
                        start = start.strip()
                        end = end.strip()

                        if start != 'HEAD':
                            start = pysvn.Revision(
                                pysvn.opt_revision_kind.number, int(start) - 1
                            )
                        else:
                            start = pysvn.Revision(pysvn.opt_revision_kind.head)

                        if end != 'HEAD':
                            end = pysvn.Revision(
                                pysvn.opt_revision_kind.number, int(end)
                            )
                        else:
                            end = pysvn.Revision(pysvn.opt_revision_kind.head)
                    else:
                        start = pysvn.Revision(
                            pysvn.opt_revision_kind.number, int(result) - 1
                        )
                        end = pysvn.Revision(
                            pysvn.opt_revision_kind.number, int(result)
                        )
                except Exception:
                    continue

                ranges.append((start, end))

        # by default merge all revisions
        if not ranges:
            ranges = [
                (
                    pysvn.Revision(pysvn.opt_revision_kind.number, 0),
                    pysvn.Revision(pysvn.opt_revision_kind.head),
                )
            ]

        self._ranges = ranges

    def setUrl(self, url):
        self._url = url

    def setTargetPath(self, path):
        self._targetPath = path

    def url(self):
        return self._url

    def targetPath(self):
        return self._targetPath


class MergeReintegrateThread(MergeThread):
    def __init__(self):
        super(MergeReintegrateThread, self).__init__()

        self.setTitle('Merge Reintegrate')

        self._url = ''
        self._targetPath = ''

    def runClient(self, client):
        """
            \remarks	checkin the information to the client
            \param		client		<pysvn.Client>
        """
        client.merge_reintegrate(
            self.url(),
            self.pegRevision(),
            self.targetPath(),
            dry_run=self.dryRun(),
            merge_options=self.additionalOptions(),
        )

    def setUrl(self, url):
        self._url = url

    def setTargetPath(self, path):
        self._targetPath = path

    def url(self):
        return self._url

    def targetPath(self):
        return self._targetPath
