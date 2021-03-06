from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import utils
from cola import qtutils
from cola import gitcmds
from cola.i18n import N_
from cola.models import main
from cola.models import selection
from cola.widgets import completion
from cola.widgets import defs
from cola.widgets import standard
from cola.compat import ustr


def run():
    files = selection.selected_group()
    if not files:
        return
    s = selection.selection()
    model = main.model()
    launch_with_head(files, bool(s.staged), model.head)


def launch_with_head(filenames, staged, head):
    args = []
    if staged:
        args.append('--cached')
    if head != 'HEAD':
        args.append(head)
    args.append('--')
    args.extend(filenames)
    launch(args)


def launch(args):
    """Launches 'git difftool' with args"""
    difftool_args = ['git', 'difftool', '--no-prompt']
    difftool_args.extend(args)
    core.fork(difftool_args)


def diff_commits(parent, a, b):
    dlg = FileDiffDialog(parent, a=a, b=b)
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtGui.QDialog.Accepted


def diff_expression(parent, expr,
                    create_widget=False, hide_expr=False):
    dlg = FileDiffDialog(parent, expr=expr, hide_expr=hide_expr)
    if create_widget:
        return dlg
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtGui.QDialog.Accepted


class FileDiffDialog(QtGui.QDialog):

    def __init__(self, parent, a=None, b=None, expr=None, title=None,
                 hide_expr=False):
        QtGui.QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)

        self.a = a
        self.b = b
        self.diff_expr = expr

        if title is None:
            title = N_('git-cola diff')

        self.setWindowTitle(title)
        self.setWindowModality(QtCore.Qt.WindowModal)

        self.expr = completion.GitRefLineEdit(parent=self)
        if expr is not None:
            self.expr.setText(expr)

        if expr is None or hide_expr:
            self.expr.hide()

        self.tree = standard.TreeWidget(self)
        self.tree.setSelectionMode(self.tree.ExtendedSelection)
        self.tree.setHeaderHidden(True)

        self.diff_button = QtGui.QPushButton(N_('Compare'))
        self.diff_button.setIcon(qtutils.ok_icon())
        self.diff_button.setEnabled(False)

        self.close_button = QtGui.QPushButton(N_('Close'))
        self.close_button.setIcon(qtutils.close_icon())

        self.button_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          qtutils.STRETCH,
                                          self.diff_button, self.close_button)

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.expr, self.tree,
                                        self.button_layout)
        self.setLayout(self.main_layout)

        self.connect(self.tree, SIGNAL('itemSelectionChanged()'),
                     self.tree_selection_changed)

        self.connect(self.tree,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self.tree_double_clicked)

        self.connect(self.expr, SIGNAL('textChanged(QString)'),
                     self.text_changed)

        self.connect(self.expr, SIGNAL('returnPressed()'),
                     self.refresh)

        qtutils.connect_button(self.diff_button, self.diff)
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        self.resize(720, 420)
        self.refresh()

    def text_changed(self, txt):
        self.diff_expr = ustr(txt)
        self.refresh()

    def refresh(self):
        if self.diff_expr is not None:
            self.diff_arg = utils.shell_split(self.diff_expr)
        elif self.b is None:
            self.diff_arg = [self.a]
        else:
            self.diff_arg = [self.a, self.b]
        self.refresh_filenames()

    def refresh_filenames(self):
        self.tree.clear()

        if self.a and self.b is None:
            filenames = gitcmds.diff_index_filenames(self.a)
        else:
            filenames = gitcmds.diff(self.diff_arg)
        if not filenames:
            return

        icon = qtutils.file_icon()
        items = []
        for filename in filenames:
            item = QtGui.QTreeWidgetItem()
            item.setIcon(0, icon)
            item.setText(0, filename)
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(filename))
            items.append(item)
        self.tree.addTopLevelItems(items)

    def tree_selection_changed(self):
        self.diff_button.setEnabled(bool(self.tree.selectedItems()))

    def tree_double_clicked(self, item, column):
        path = item.data(0, QtCore.Qt.UserRole).toPyObject()
        launch(self.diff_arg + ['--', ustr(path)])

    def diff(self):
        items = self.tree.selectedItems()
        if not items:
            return
        paths = [i.data(0, QtCore.Qt.UserRole).toPyObject() for i in items]
        for path in paths:
            launch(self.diff_arg + ['--', ustr(path)])
