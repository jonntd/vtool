global type_QT

import util
import util_file
import threading
import string
import random

try:
    from PySide import QtCore, QtGui
    try:
        from shiboken import wrapInstance
    except:
        try:
            from PySide.shiboken import wrapInstance
        except:
            pass
    type_QT = 'pyside'
    print 'using pyside'
except:
    type_QT = None

if not type_QT == 'pyside':
    try:
        import PyQt4
        from PyQt4 import QtGui, QtCore, Qt, uic
        import sip
        type_QT = 'pyqt'
        print 'using pyqt'
        
    except:
        type_QT = None
        pass
    

def is_pyqt():
    global type_QT
    if type_QT == 'pyqt':
        return True
    return False
    
def is_pyside():
    global type_QT
    if type_QT == 'pyside':
        return True
    return False

def build_qt_application(*argv):
    application = QtGui.QApplication(*argv)
    return application

def create_signal(*arg_list):
        
    if is_pyqt():
        return QtCore.pyqtSignal(*arg_list)
    if is_pyside():
        return QtCore.Signal(*arg_list)

class BasicGraphicsView(QtGui.QGraphicsView):
    
    def __init__(self):
        
        super(BasicGraphicsView, self).__init__()
                
        self.scene = QtGui.QGraphicsScene()
        #self.scene.set
        
        button = QtGui.QGraphicsRectItem(20,20,20,20)
        
        button.setFlags(QtGui.QGraphicsItem.ItemIsMovable)
        button.setFlags(QtGui.QGraphicsItem.ItemIsSelectable)
        
        graphic = QtGui.QGraphicsPixmapItem()
        
        
        self.scene.addItem(button)
        
        self.setScene(self.scene)

class BasicWindow(QtGui.QMainWindow):
    
    title = 'BasicWindow'

    def __init__(self, parent = None):
        super(BasicWindow, self).__init__(parent)
        
        self.setWindowTitle(self.title)
        self.setObjectName(self.title)
        
        main_widget = QtGui.QWidget()
        
        self.main_layout = self._define_main_layout()
        main_widget.setLayout(self.main_layout)
        
        self.setCentralWidget( main_widget )
        
        self.main_layout.expandingDirections()
        self.main_layout.setContentsMargins(1,1,1,1)
        self.main_layout.setSpacing(2)
        
        self._build_widgets()
        
    def _define_main_layout(self):
        return QtGui.QVBoxLayout()
    
    def _build_widgets(self):
        return
       
class DirectoryWindow(BasicWindow):
    
    def __init__(self, parent = None):
        
        self.directory = None
        
        super(DirectoryWindow, self).__init__(parent)
        
    def set_directory(self, directory):
        self.directory = directory
       
class BasicWidget(QtGui.QWidget):

    def __init__(self, parent = None):
        super(BasicWidget, self).__init__()
        
        self.main_layout = self._define_main_layout() 
        self.main_layout.setContentsMargins(2,2,2,2)
        self.main_layout.setSpacing(2)
        
        self.setLayout(self.main_layout)
        
        self._build_widgets()

    def _define_main_layout(self):
        layout = QtGui.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        return layout
        
    def _build_widgets(self):
        pass
        
class BasicDockWidget(QtGui.QDockWidget):
    def __init__(self, parent = None):
        super(BasicWidget, self).__init__()
        
        self.main_layout = self._define_main_layout() 
        self.main_layout.setContentsMargins(2,2,2,2)
        self.main_layout.setSpacing(2)
        
        self.setLayout(self.main_layout)
        
        self._build_widgets()

    def _define_main_layout(self):
        layout = QtGui.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        return layout
        
    def _build_widgets(self):
        pass

        
class DirectoryWidget(BasicWidget):
    def __init__(self, parent = None):
        
        self.directory = None
        self.last_directory = None
        
        super(DirectoryWidget, self).__init__()
        
        
        
    def set_directory(self, directory):
        
        self.last_directory = self.directory
        self.directory = directory
     
    
       
class TreeWidget(QtGui.QTreeWidget):
    
    item_clicked = create_signal(object, object)    
    
    def __init__(self):
        super(TreeWidget, self).__init__()

        self.title_text_index = 0

        self.itemExpanded.connect(self._item_expanded)

        self.setExpandsOnDoubleClick(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        self.sortByColumn(self.title_text_index, QtCore.Qt.AscendingOrder)
        
        self.itemActivated.connect(self._item_activated)
        self.itemChanged.connect(self._item_changed)
        self.itemSelectionChanged.connect(self._item_selection_changed)
        self.itemClicked.connect(self._item_clicked)
        
        self.text_edit = True
        self.edit_state = None
        self.old_name = None
        
        self.last_item = None
        self.current_item = None
        self.current_name = None
        
        if util.is_in_nuke():
            self.setAlternatingRowColors(False)
                
        if not util.is_in_maya() and not util.is_in_nuke():
            palette = QtGui.QPalette()
            palette.setColor(palette.Highlight, QtCore.Qt.gray)
            self.setPalette(palette)
    
    def _define_item(self):
        return QtGui.QTreeWidgetItem()
    
    def _define_item_size(self):
        return 
        
    def _clear_selection(self):
        
        self.clearSelection()
        self.current_item = None
        
        if self.edit_state:
            self._edit_finish(self.last_item)
            
    def _item_clicked(self, item, column):
        self.last_item = self.current_item
        
        self.current_item = self.currentItem()

        if not item or column != self.title_text_index:
            if self.last_item:
                self._clear_selection()
                
        self._emit_item_click(item)
                
    def _emit_item_click(self, item):
        
        name = item.text(self.title_text_index)
        self.item_clicked.emit(name, item)
    
    def mousePressEvent(self, event):
        super(TreeWidget, self).mousePressEvent(event)
        
        item = self.itemAt(event.x(), event.y())
                
        if not item:
            self._clear_selection()
                          
    def _item_selection_changed(self):
        
        current_item = self.currentItem()
        item_list = self.selectedItems()
        
        if item_list:
            current_item = item_list[0]
        
        if current_item:
            self.current_name = current_item.text(self.title_text_index)
        
        if self.edit_state:
            self._edit_finish(self.edit_state)
            
        if current_item:
            self._emit_item_click(current_item)        
            
    def _item_changed(self, current_item, previous_item):
          
        self._edit_finish(previous_item)                      
        
    def _item_activated(self, item):
        
        if not self.edit_state:
            
            if self.text_edit:
                self._edit_start(item)
            return
                
        if self.edit_state:
            self._edit_finish(self.edit_state)
            
            return
            
    def _item_expanded(self, item):
        self._add_sub_items(item) 
        self.resizeColumnToContents(self.title_text_index)
        
    def _edit_start(self, item):
        
        self.old_name = str(item.text(self.title_text_index))
        
        self.openPersistentEditor(item, self.title_text_index)
        self.edit_state = item
        return
        
    def _edit_finish(self, item):
        
        if self.edit_state == None:
            return
        
        self.edit_state = None
        
        self.closePersistentEditor(item, self.title_text_index)
        
        if type(item) == int:
            return self.current_item
        
        if not self._item_rename_valid(self.old_name, item):
            
            item.setText(self.title_text_index, self.old_name )
            
            return item
        
        if self._item_rename_valid(self.old_name, item):
            
            self._item_renamed(item)
            return item
        
        return item
    
    def _item_rename_valid(self, old_name, item):
        
        new_name = item.text(self.title_text_index)
        
        if old_name == new_name:
            return False
        if old_name != new_name:
            return True
    
    def _item_renamed(self, item):
        return

    def _delete_children(self, item):
        self.delete_tree_item_children(item)
        
    def _add_sub_items(self, item):
        pass
        
    def addTopLevelItem(self, item):
        
        super(TreeWidget, self).addTopLevelItem(item)
        
        if hasattr(item, 'widget'):
            if hasattr(item, 'column'):
                self.setItemWidget(item, item.column, item.widget)
                
            if not hasattr(item, 'column'):
                self.setItemWidget(item, 0, item.widget)
                
    def insertTopLevelItem(self, index, item):
        super(TreeWidget, self).insertTopLevelItem(index, item)
        
        if hasattr(item, 'widget'):
            if hasattr(item, 'column'):
                self.setItemWidget(item, item.column, item.widget)
                
            if not hasattr(item, 'column'):
                self.setItemWidget(item, 0, item.widget)
           
    def unhide_items(self):
            
        for inc in range( 0, self.topLevelItemCount() ):
            item = self.topLevelItem(inc)
            self.setItemHidden(item, False)

    def filter_names(self, string):
        
        self.unhide_items()
                        
        for inc in range( 0, self.topLevelItemCount() ):
                
            item = self.topLevelItem(inc)
            text = str( item.text(self.title_text_index) )
                                                
            if not text.startswith(string) and not text.startswith(string.upper()):
                
                self.setItemHidden(item, True)  
            
    def get_tree_item_path(self, tree_item):
                
        parent_items = []
        parent_items.append(tree_item)
        
        parent_item = tree_item.parent()
        
        while parent_item:
            parent_items.append(parent_item)
            
            parent_item = parent_item.parent()
            
        return parent_items
    
    def get_tree_item_names(self, tree_items):
        
        item_names = []
        
        for tree_item in tree_items:
            name = self.get_tree_item_name(tree_item)
            item_names.append(name)    
            
        return item_names
    
    def get_tree_item_name(self, tree_item):
        count = QtGui.QTreeWidgetItem.columnCount( tree_item )
            
        name = []
            
        for inc in range(0, count):
                
            name.append( str( tree_item.text(inc) ) )
            
        return name
    
    def get_item_path_string(self, item):
        
        parents = self.get_tree_item_path(item)
        parent_names = self.get_tree_item_names(parents)
        
        names = []
        
        for name in parent_names:
            names.append(name[0])
        
        names.reverse()
        
        path = string.join(names, '/')
        
        return path
    
    def delete_tree_item_children(self, tree_item):
        count = tree_item.childCount()
        
        if count <= 0:
            return
        
        children = tree_item.takeChildren()
            
        for child in children:
            del(child)
            
    def get_tree_item_children(self, tree_item):
        count = tree_item.childCount()
        
        items = []
        
        for inc in range(0, count):
            items.append( tree_item.child(inc) )
        
        return items
    
    def set_text_edit(self, bool_value):
        self.text_edit = bool_value
        
class TreeWidgetItem(QtGui.QTreeWidgetItem):
    
    def __init__(self, parent = None):
        self.widget = self._define_widget()
        if self.widget:
            self.widget.item = self
                
        self.column = self._define_column()
        
        super(TreeWidgetItem, self).__init__(parent)
        
        
    def _define_widget(self):
        return
    
    def _define_column(self):
        return 0
        
     
class TreeItemWidget(BasicWidget):
        
    def __init__(self, parent = None):
        self.label = None
        
        super(TreeItemWidget, self).__init__(parent)
        
    def _define_main_layout(self):
        return QtGui.QHBoxLayout()
    
    def _build_widgets(self):
        self.label = QtGui.QLabel()
        
        self.main_layout.addWidget(self.label)
    
    def set_text(self, text):
        self.label.setText(text)
        
    def get_text(self):
        return self.label.text()
        
class TreeItemFileWidget(TreeItemWidget):
    pass
        
class FileTreeWidget(TreeWidget):
    
    refreshed = create_signal()
    
    def __init__(self):
        self.directory = None
        
        super(FileTreeWidget, self).__init__()
        
        self.setHeaderLabels(self._define_header())
    
    def _define_new_branch_name(self):
        return 'new_folder'  
        
    def _define_header(self):
        return ['name','size','date']

    def _define_item(self):
        return QtGui.QTreeWidgetItem()
    
    def _define_exclude_extensions(self):
        return
    

    def _get_files(self, directory = None):
        
        if not directory:
            directory = self.directory
            
        return util_file.get_files_and_folders(directory)
    
    def _load_files(self, files):
        self.clear()
        
        self._add_items(files)
        
    def _add_items(self, files):
        
        for util_file in files:
            self._add_item(util_file)

    def _add_item(self, filename, parent = None):
        
        exclude = self._define_exclude_extensions()
        
        if exclude:
            split_name = filename.split('.')
            extension = split_name[-1]
    
            if extension in exclude:
                return
        
        item = self._define_item()
        
        size = self._define_item_size()
        if size:
            size = QtCore.QSize(*size)
            
            item.setSizeHint(self.title_text_index, size)
        path_name = filename
        
        if parent:
            parent_path = self.get_item_path_string(parent)
            path_name = '%s/%s' % (parent_path, filename)
            
        
        path = util_file.join_path(self.directory, path_name)
        
        sub_files = util_file.get_files_and_folders(path)
                
        item.setText(self.title_text_index, filename)
        
        if util_file.is_file(path):
            size = util_file.get_filesize(path)
            date = util_file.get_last_modified_date(path)
            
            item.setText(self.title_text_index+1, str(size))
            item.setText(self.title_text_index+2, str(date))
        
        if sub_files:
            
            
            exclude_extensions = self._define_exclude_extensions()
            exclude_count = 0
        
            if exclude_extensions:
                for file in sub_files:
                    for exclude in exclude_extensions:
                        if file.endswith(exclude):
                            exclude_count += 1
                            break
            
            if exclude_count != len(sub_files):
                QtGui.QTreeWidgetItem(item)
            
        if not parent:
            self.addTopLevelItem(item)
        if parent:
            parent.addChild(item)
            
        return item
        
    def _add_sub_items(self, item):
        self._delete_children(item)
                
        path_string = self.get_item_path_string(item)
        
        path = util_file.join_path(self.directory, path_string)
        
        files = self._get_files(path)
        
        self._add_items(files)
        
            
    def create_branch(self, name = None):
        
        current_item = self.current_item
        
        if current_item:
            path = self.get_item_path_string(self.current_item)
            path = util_file.join_path(self.directory, path)
            
            if util_file.is_file(path):
                path = util_file.get_dirname(path)
                current_item = self.current_item.parent()
            
        if not current_item:
            path = self.directory
                
        folder = util_file.FolderEditor(path)
        
        if not name:
            name = self._define_new_branch_name()
            
        folder.create(name)
        
        if current_item:
            self._add_sub_items(current_item)
            self.setItemExpanded(current_item, True)
            
        if not current_item:
            self.refresh()
            
    def delete_branch(self):
        item = self.current_item
        path = self.get_item_directory(item)
        
        name = util_file.get_basename(path)
        directory = util_file.get_dirname(path)
        
        if util_file.is_dir(path):
            util_file.delete_dir(name, directory)
        if util_file.is_file(path):
            util_file.delete_file(name, directory)
            if path.endswith('.py'):
                util_file.delete_file((name+'c'), directory)
        
        index = self.indexOfTopLevelItem(item)
        
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        if not parent:
            self.takeTopLevelItem(index)

    def refresh(self):
        files = self._get_files()
        
        if not files:
            self.clear()
            return
        
        self._load_files(files)
        self.refreshed.emit()

    def get_item_directory(self, item):
        
        path_string = self.get_item_path_string(item)
        
        return util_file.join_path(self.directory, path_string)

    def set_directory(self, directory):
        
        self.directory = directory
        self.refresh()
        
class EditFileTreeWidget(DirectoryWidget):
    
    description = 'EditTree'
    
    item_clicked = create_signal(object, object)
    
    def __init__(self, parent = None):        
        
        self.tree_widget = None
        
        super(EditFileTreeWidget, self).__init__(parent) 
        
    def _define_tree_widget(self):
        return FileTreeWidget()
    
    def _define_manager_widget(self):
        return ManageTreeWidget()
    
    def _define_filter_widget(self):
        return FilterTreeWidget()
        
    def _build_widgets(self):
        
        
        self.tree_widget = self._define_tree_widget()   
        
        self.tree_widget.item_clicked.connect(self._item_clicked)
        
          
        self.manager_widget = self._define_manager_widget()
        self.filter_widget = self._define_filter_widget()
        
        self.filter_widget.set_tree_widget(self.tree_widget)
        self.filter_widget.set_directory(self.directory)
        self.manager_widget.set_tree_widget(self.tree_widget)
        
        self.main_layout.addWidget(self.tree_widget)
        self.main_layout.addWidget(self.filter_widget)
        self.main_layout.addWidget(self.manager_widget)
        
    def _item_clicked(self, name, item):
        self.item_clicked.emit(name, item)

    def get_current_item(self):
        return self.tree_widget.current_item
    
    def get_current_item_name(self):
        return self.tree_widget.current_name
    
    def get_current_item_directory(self):
        item = self.get_current_item()
        return self.tree_widget.get_item_directory(item)

    def refresh(self):
        self.tree_widget.refresh()
    
    def set_directory(self, directory, sub = False):
        super(EditFileTreeWidget, self).set_directory(directory)
        
        if not sub:
            self.directory = directory
            
        self.tree_widget.set_directory(directory)
        self.filter_widget.set_directory(directory)
        
        if hasattr(self.manager_widget, 'set_directory'):
            self.manager_widget.set_directory(directory)
       
class ManageTreeWidget(BasicWidget):
        
    def __init__(self):
        
        self.tree_widget = None
        
        super(ManageTreeWidget,self).__init__()
    
    def set_tree_widget(self, tree_widget):
        self.tree_widget = tree_widget
       
class FilterTreeWidget( DirectoryWidget ):
    
    def __init__(self):
        
        self.tree_widget = None
        
        super(FilterTreeWidget, self).__init__()
    
    def _define_main_layout(self):
        return QtGui.QHBoxLayout()
    
    def _build_widgets(self): 
        self.filter_names = QtGui.QLineEdit()
        self.filter_names.setPlaceholderText('filter names')
        self.sub_path_filter = QtGui.QLineEdit()
        self.sub_path_filter.setPlaceholderText('set sub path')
        self.sub_path_filter.textChanged.connect(self._sub_path_filter_changed)
        
        self.filter_names.textChanged.connect(self._filter_names)
                
        self.main_layout.addWidget(self.filter_names)
        self.main_layout.addWidget(self.sub_path_filter)
        
    def _filter_names(self, text):
        
        self.tree_widget.filter_names(text)
        self.skip_name_filter = False
        
    def _sub_path_filter_changed(self):
        current_text = self.sub_path_filter.text()
        current_text = current_text.strip()
        
        if not current_text:
            self.set_directory(self.directory)
            self.tree_widget.set_directory(self.directory)
            return
            
        sub_dir = util_file.join_path(self.directory, current_text)
        if not sub_dir:
            return
        
        if util_file.is_dir(sub_dir):
            self.tree_widget.set_directory(sub_dir)
            
    def clear_sub_path_filter(self):
        self.sub_path_filter.setText('')
            
    def set_tree_widget(self, tree_widget):
        self.tree_widget = tree_widget
        
    
        
class FileManagerWidget(DirectoryWidget):
    
    def __init__(self, parent = None):
        super(FileManagerWidget, self).__init__(parent)
        
        self.data_class = self._define_data_class()
        self.save_widget.set_data_class(self.data_class)
        self.history_widget.set_data_class(self.data_class)
        
        self.history_attached = False
        
    def _define_main_layout(self):
        return QtGui.QHBoxLayout()
        
    def _define_data_class(self):
        return
    
    def _define_main_tab_name(self):
        return 'Data File'
    
    def _build_widgets(self):
        
        self.tab_widget = QtGui.QTabWidget()
        
        self.main_tab_name = self._define_main_tab_name()
        self.version_tab_name = 'Version'
                
        self.save_widget = self._define_save_widget()
        
        self.save_widget.file_changed.connect(self._file_changed)
                
        self.tab_widget.addTab(self.save_widget, self.main_tab_name)
        self._add_history_widget()
        self.tab_widget.currentChanged.connect(self._tab_changed)
                
        self.main_layout.addWidget(self.tab_widget)
        
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

    def _add_history_widget(self):
        self.history_buffer_widget = BasicWidget()
        
        self.history_widget = self._define_history_widget()
        self.history_widget.file_changed.connect(self._file_changed)
        
        
        self.tab_widget.addTab(self.history_buffer_widget, self.version_tab_name)
        
        self.history_widget.hide()
        
    def _define_save_widget(self):
        return SaveFileWidget()
        
    def _define_history_widget(self):
        return HistoryFileWidget()
        
    def _tab_changed(self):
                                
        if self.tab_widget.currentIndex() == 0:
            
            self.history_widget.hide()
            self.history_widget.refresh()
            
            self.save_widget.set_directory(self.directory)
            
            if self.history_attached:
                self.history_buffer_widget.main_layout.removeWidget(self.history_widget)
            
            self.history_attached = False
                
        if self.tab_widget.currentIndex() == 1:
            self.update_history()
                        
    def _file_changed(self):
        if not util_file.is_dir(self.directory):     
            return
        
        self._activate_history_tab()
        
    def _activate_history_tab(self):
        version_tool = util_file.VersionFile(self.directory)    
        files = version_tool.get_versions()
        
        if files:
            self.tab_widget.setTabEnabled(1, True)
        if not files:
            self.tab_widget.setTabEnabled(1, False) 
        
    def update_history(self):
        self.history_buffer_widget.main_layout.addWidget(self.history_widget)
            
        self.history_widget.show()
        self.history_widget.set_directory(self.directory)
        self.history_widget.refresh()
        self.history_attached = True
        
        self._activate_history_tab()
        
        
        
        
        
    def set_directory(self, directory):
        super(FileManagerWidget, self).set_directory(directory)
        
        if self.tab_widget.currentIndex() == 0:
            self.save_widget.set_directory(directory)
        
        if self.tab_widget.currentIndex() == 1:
            self.history_widget.set_directory(directory)
        
        if self.data_class:
            self.data_class.set_directory(directory)
            
        self._file_changed()
        
        
class SaveFileWidget(DirectoryWidget):
    
    file_changed = create_signal()
    
    def __init__(self, parent = None):
        super(SaveFileWidget, self).__init__(parent)
        
        self.data_class = None
        
    def _define_main_layout(self):
        return QtGui.QHBoxLayout()
        
    def _build_widgets(self):
        
        self.save_button = QtGui.QPushButton('Save')
        load_button = QtGui.QPushButton('Open Latest')
        
        self.save_button.clicked.connect(self._save)
        load_button.clicked.connect(self._open)
        
        self.main_layout.addWidget(load_button)
        self.main_layout.addWidget(self.save_button)
        
        
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

    def _save(self):
        
        self.file_changed.emit()
    
    def _open(self):
        pass

    def set_data_class(self, data_class_instance):
        self.data_class = data_class_instance
        
        if self.directory:
            self.data_class.set_directory(self.directory)
    
    def set_directory(self, directory):
        super(SaveFileWidget, self).set_directory(directory)
        
        if self.data_class:
            self.data_class.set_directory(self.directory)
            
    def set_no_save(self):
        self.save_button.setDisabled(True)
    
class HistoryTreeWidget(FileTreeWidget):
    

    def __init__(self):
        super(HistoryTreeWidget, self).__init__()
        
        if is_pyside():
            self.sortByColumn(0, QtCore.Qt.SortOrder.DescendingOrder)
            
        self.setColumnWidth(0, 70)  
        self.setColumnWidth(1, 150)
        self.setColumnWidth(2, 50)
        self.setColumnWidth(3, 50)
        
        self.padding = 1
    
    def _item_activated(self, item):
        return
        
    def _define_header(self):
        return ['version','comment','size','user','date']
    
    def _get_files(self):

        if self.directory:
            
            version_tool = util_file.VersionFile(self.directory)
            
            files = version_tool.get_versions()
            
            if not files:
                return
            
            if files:
                self.padding = len(str(len(files)))
                return files
    
    def _add_item(self, filename):
        
        split_name = filename.split('.')
        if len(split_name) == 1:
            return
        
        try:
            version_int = int(split_name[-1])
        except:
            return
        
        version_tool = util_file.VersionFile(self.directory)
        version_file = version_tool.get_version_path(version_int)
        comment, user = version_tool.get_version_data(version_int)
        file_size = util_file.get_filesize(version_file)
        file_date = util_file.get_last_modified_date(version_file)
        
        version_str = str(version_int).zfill(self.padding)
        
        item = QtGui.QTreeWidgetItem()
        item.setText(0, version_str)
        item.setText(1, comment)
        item.setText(2, str(file_size))
        item.setText(3, user)
        item.setText(4, file_date)
        
        self.addTopLevelItem(item)
        item.filepath = version_file

class HistoryFileWidget(DirectoryWidget):
    
    file_changed = create_signal()
    
    def _define_main_layout(self):
        return QtGui.QVBoxLayout()
    
    def _define_list(self):
        return HistoryTreeWidget()
    
    def _build_widgets(self):
        
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                           QtGui.QSizePolicy.MinimumExpanding)
        
        self.button_layout = QtGui.QHBoxLayout()
        
        open_button = QtGui.QPushButton('Open')
        open_button.clicked.connect(self._open_version)
                
        self.button_layout.addWidget(open_button)
        
        self.version_list = self._define_list()
        
                
        self.main_layout.addWidget(self.version_list)
        self.main_layout.addLayout(self.button_layout)

    def _open_version(self):
        pass
            
    def refresh(self):
        self.version_list.refresh()
                
    def set_data_class(self, data_class_instance):
        self.data_class = data_class_instance
        
        if self.directory:
            self.data_class.set_directory(self.directory)
        
    def set_directory(self, directory):
        
        super(HistoryFileWidget, self).set_directory(directory)
        
        self.version_list.set_directory(directory)    

class GetString(BasicWidget):
    
    text_changed = create_signal(object)
    
    def __init__(self, name, parent = None):
        self.name = name
        super(GetString, self).__init__(parent)
    
    def _define_main_layout(self):
        return QtGui.QHBoxLayout()
            
    def _build_widgets(self):
        
        self.text_entry = QtGui.QLineEdit()
        #self.text_entry.setMaximumWidth(100)
        
        self.label = QtGui.QLabel(self.name)
        self.label.setAlignment(QtCore.Qt.AlignRight)
        self.label.setMinimumWidth(70)
        self._setup_text_widget()
        
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.text_entry)
        
    def _setup_text_widget(self):
        self.text_entry.textChanged.connect(self._text_changed)
                    
    def _text_changed(self):
        self.text_changed.emit(self.text_entry.text())
        
    def set_text(self, text):
        self.text_entry.setText(text)
        
    def get_text(self):
        return self.text_entry.text()
        
    def set_label(self, label):
        self.label.setText(label)  
        
    def set_password_mode(self, bool_value):
        
        if bool_value:
            self.text_entry.setEchoMode(self.text_entry.Password)
        if not bool_value:
            self.text_entry.setEchoMode(self.text_entry.Normal) 
    
    

class GetDirectoryWidget(DirectoryWidget):
    
    directory_changed = create_signal(object)
    
    def __init__(self, parent = None):
        super(GetDirectoryWidget, self).__init__(parent)
        
        self.label = 'directory'
    
    def _define_main_layout(self):
        return QtGui.QHBoxLayout()
    
    def _build_widgets(self):
        
        self.directory_label = QtGui.QLabel('directory')
        self.directory_label.setMinimumWidth(100)
        self.directory_label.setMaximumWidth(100)
        
        self.directory_edit = QtGui.QLineEdit()
        self.directory_edit.textChanged.connect(self._text_changed)
        directory_browse = QtGui.QPushButton('browse')
        
        directory_browse.clicked.connect(self._browser)
        
        self.main_layout.addWidget(self.directory_label)
        self.main_layout.addWidget(self.directory_edit)
        self.main_layout.addWidget(directory_browse)
        
    def _browser(self):
        
        filename = get_file(self.get_directory() , self)
        
        filename = util_file.fix_slashes(filename)
        
        if filename and util_file.is_dir(filename):
            self.directory_edit.setText(filename)
            self.directory_changed.emit(filename)
        
    def _text_changed(self):
        
        directory = self.get_directory()
        
        if util_file.is_dir(directory):
            self.directory_changed.emit(directory)
        
    def set_label(self, label):
        self.directory_label.setText(label)
        
    def set_directory(self, directory):
        super(GetDirectoryWidget, self).set_directory(directory)
        
        self.directory_edit.setText(directory)
        
    def get_directory(self):
        return self.directory_edit.text()
     
class GetNumber(BasicWidget):
    
    valueChanged = create_signal(object)
    
    def __init__(self, name, parent = None):
        self.name = name
        super(GetNumber, self).__init__(parent)
    
    def _define_main_layout(self):
        return QtGui.QHBoxLayout()
    
    def _define_spin_widget(self):
        return QtGui.QDoubleSpinBox()
    
    def _build_widgets(self):
        self.spin_widget = self._define_spin_widget()
        self.spin_widget.setMaximumWidth(100)
        
        self.label = QtGui.QLabel(self.name)
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self._setup_spin_widget()
        
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.spin_widget)
        
    def _setup_spin_widget(self):
        
        if hasattr(self.spin_widget, 'CorrectToNearestValue'):
            self.spin_widget.setCorrectionMode(self.spin_widget.CorrectToNearestValue)
            
        if hasattr(self.spin_widget, 'setWrapping'):
            self.spin_widget.setWrapping(False)
            
        self.spin_widget.setMaximum(100000000)
        
        self.spin_widget.valueChanged.connect(self._value_changed)
                    
    def _value_changed(self):
        self.valueChanged.emit(self.spin_widget.value())
        
    def set_value(self, value):
        self.spin_widget.setValue(value)
        
    def set_label(self, label):
        self.label.setText(label)
             
class GetNumberButton(GetNumber):
    
    clicked = create_signal(object)
    
    def _build_widgets(self):   
        super(GetNumberButton, self)._build_widgets()
        
        self.button = QtGui.QPushButton('run')
        self.button.clicked.connect(self._clicked)
        self.button.setMaximumWidth(60)
        
        self.main_layout.addWidget(self.button)
        
    def _clicked(self):
        self.clicked.emit(self.spin_widget.value())
        
class GetIntNumberButton(GetNumberButton):
    def _define_spin_widget(self):
        spin_widget = QtGui.QSpinBox()
        return spin_widget
       
class ProgressBar(QtGui.QProgressBar):
    
    def set_count(self, count):
        
        self.setMinimum(0)
        self.setMaximum(count)
        
    def set_increment(self, int_value):
        self.setValue(int_value)
        
class LoginWidget( BasicWidget ):
    
    login = create_signal(object, object)
    
    def _build_widgets(self):
        
        group_widget = QtGui.QGroupBox('Login')
        group_layout = QtGui.QVBoxLayout()
        group_widget.setLayout(group_layout)
        
        self.login_widget = GetString('User: ')
        self.password_widget = GetString('Password: ')
        self.password_widget.set_password_mode(True)
        
        self.login_state = QtGui.QLabel('Login failed.')
        self.login_state.hide()
        
        login_button = QtGui.QPushButton('Enter')

        login_button.clicked.connect( self._login )
        
        self.password_widget.text_entry.returnPressed.connect(self._login)

        group_layout.addWidget(self.login_widget)
        group_layout.addWidget(self.password_widget)
        group_layout.addWidget(login_button)
        group_layout.addWidget(self.login_state)

        self.main_layout.addWidget(group_widget)
        
        self.group_layout = group_layout

        
    def _login(self):
        
        login = self.login_widget.get_text()
                
        password = self.password_widget.get_text()
        
        self.login.emit(login, password)
        
    def set_login(self, text):
        self.login_widget.set_text(text)
        
    def set_login_failed(self, bool_value):
        if bool_value:
            self.login_state.show()
            
        if not bool_value:
            self.login_state.hide()
        
class CodeTextEdit(QtGui.QPlainTextEdit):
    
    save = create_signal()
    
    def __init__(self):
        
        self.filepath = None
        
        super(CodeTextEdit, self).__init__()
        
        shortcut = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+s")), self)
        shortcut.activated.connect(self._save)
        
        self._setup_highlighter()
        
        
        
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)
                
    def _setup_highlighter(self):
        self.highlighter = Highlighter(self.document())
    
    def _save(self):
        self.save.emit()
    
    def keyPressEvent(self, event):
        
        pass_on = True
        
        if event.key() == QtCore.Qt.Key_Tab:
            self.insertPlainText('    ')
            pass_on = False
        
        if pass_on:
            super(CodeTextEdit, self).keyPressEvent(event)
    
    def set_file(self, filepath):
        
        in_file = QtCore.QFile(filepath)
        
        if in_file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text):
            text = in_file.readAll()
            
            text = str(text)
            
            self.setPlainText(text)
            
        self.filepath = filepath
    
            
class Highlighter(QtGui.QSyntaxHighlighter):
    
    def __init__(self, parent=None):
        super(Highlighter, self).__init__(parent)

        

        keywordFormat = QtGui.QTextCharFormat()
        keywordFormat.setForeground(QtGui.QColor(0, 150, 150))
        keywordFormat.setFontWeight(QtGui.QFont.Bold)

        keywordPatterns = ["\\bdef\\b", "\\bclass\\b", "\\bimport\\b","\\breload\\b", '\\bpass\\b','\\breturn\\b']

        self.highlightingRules = [(QtCore.QRegExp(pattern), keywordFormat)
                for pattern in keywordPatterns]

        classFormat = QtGui.QTextCharFormat()
        classFormat.setFontWeight(QtGui.QFont.Bold)
        #classFormat.setForeground(QtCore.Qt.blue)
        self.highlightingRules.append((QtCore.QRegExp("\\b\.[a-zA-Z_]+\\b(?=\()"),
                classFormat))

        

        numberFormat = QtGui.QTextCharFormat()
        numberFormat.setForeground(QtCore.Qt.cyan)
        self.highlightingRules.append((QtCore.QRegExp("[0-9]+"), numberFormat))
        

        
        quotationFormat = QtGui.QTextCharFormat()
        quotationFormat.setForeground(QtCore.Qt.darkGreen)
        self.highlightingRules.append((QtCore.QRegExp("\'[^\']*\'"),
                quotationFormat))
        self.highlightingRules.append((QtCore.QRegExp("\"[^\"]*\""),
                quotationFormat))
        
        
        
        singleLineCommentFormat = QtGui.QTextCharFormat()
        singleLineCommentFormat.setForeground(QtCore.Qt.red)
        self.highlightingRules.append((QtCore.QRegExp("#.*"),
                singleLineCommentFormat))

        """
        functionFormat = QtGui.QTextCharFormat()
        functionFormat.setFontItalic(True)
        functionFormat.setForeground(QtCore.Qt.blue)
        self.highlightingRules.append((QtCore.QRegExp("\\b[A-Za-z0-9_]+(?=\\()"),
                functionFormat))
        """

        self.multiLineCommentFormat = QtGui.QTextCharFormat()
        self.multiLineCommentFormat.setForeground(QtCore.Qt.darkGray)
        
        self.commentStartExpression = QtCore.QRegExp('"""')
        self.commentEndExpression = QtCore.QRegExp('"""')
        
    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)
        endIndex = -1

        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = self.commentStartExpression.indexIn(text)

        while startIndex >= 0:
            endIndex = self.commentEndExpression.indexIn(text, startIndex)
            
            if endIndex == -1 or endIndex == startIndex:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
                
            else:
                commentLength = endIndex - startIndex + self.commentEndExpression.matchedLength()

            self.setFormat(startIndex, commentLength,
                    self.multiLineCommentFormat)
            startIndex = self.commentStartExpression.indexIn(text,
                    startIndex + commentLength);

#--- Custom Painted Widgets

class TimelineWidget(QtGui.QWidget):

    def __init__(self):
        super(TimelineWidget, self).__init__()
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.setMaximumHeight(120)
        self.setMinimumHeight(80)
        self.values = []
        self.skip_random = False
        
    def sizeHint(self):
        return QtCore.QSize(100,80)
       
    def paintEvent(self, e):

        painter = QtGui.QPainter()
        
        painter.begin(self)
                        
        if not self.values and not self.skip_random:
            self._draw_random_lines(painter)
            
        if self.values or self.skip_random:
            self._draw_lines(painter)
            
        self._draw_frame(painter)
            
        painter.end()
        
    def _draw_frame(self, painter):
        
        pen = QtGui.QPen(QtCore.Qt.gray)
        pen.setWidth(2)
        painter.setPen(pen)
        
        height_offset = 20
        
        size = self.size()
        
        width = size.width()
        height = size.height()
        
        section = (width-21.00)/24.00
        accum = 10.00
        
        for inc in range(0, 25):
            
            value = inc
            
            if inc > 12:
                value = inc-12
                
            painter.drawLine(accum, height-(height_offset+1), accum, 30)
            
            sub_accum = accum + (section/2.0)
            
            painter.drawLine(sub_accum, height-(height_offset+1), sub_accum, height-(height_offset+11))
            
            painter.drawText(accum-15, height-(height_offset+12), 30,height-(height_offset+12), QtCore.Qt.AlignCenter, str(value))
            
            accum+=section
        
    def _draw_random_lines(self, painter):
      
        pen = QtGui.QPen(QtCore.Qt.green)
        pen.setWidth(2)
        
        height_offset = 20
        
        painter.setPen(pen)
        
        size = self.size()
        
        for i in range(500):
            x = random.randint(10, size.width()-11)               
            painter.drawLine(x,10,x,size.height()-(height_offset+2))
            
    def _draw_lines(self, painter):
        
        pen = QtGui.QPen(QtCore.Qt.green)
        pen.setWidth(3)
        
        height_offset = 20
        
        painter.setPen(pen)
        
        size = self.size()
        
        if not self.values:
            return
        
        for inc in range(0, len(self.values)):
            
            width = size.width()-21
            
            x_value = (width * self.values[inc]) / 24.00  
                        
            x_value += 10
                         
            painter.drawLine(x_value,10,x_value,size.height()-(height_offset+2))
        
    def set_values(self, value_list):
        self.skip_random = True
        self.values = value_list
        
def get_comment(parent = None,text_message = 'add comment'):
    commentDialog = QtGui.QInputDialog(parent)
    commentDialog.setTextValue('comment')            
    comment, ok = QtGui.QInputDialog.getText(parent, 'util_file save',text_message)
    
    comment = comment.replace('\\', '_')
    
    if ok:
        return comment
    
def get_file(directory, parent = None):
    fileDialog = QtGui.QFileDialog(parent)
    
    if directory:
        fileDialog.setDirectory(directory)
    
    directory = fileDialog.getExistingDirectory()
    
    return directory

def get_permission(message, parent = None):
    
    message_box = QtGui.QMessageBox(parent)
    
    message = message_box.question(parent, 'Question', message, message_box.Yes | message_box.No )
    
    if message == message_box.Yes:
        return True
    
    if message == message_box.No:
        return False
    
def critical(message, parent = None):
    
    message_box = QtGui.QMessageBox(parent)
    
    message_box.critical(parent, 'Critical Error', message)

    