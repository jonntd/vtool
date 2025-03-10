# Copyright (C) 2022 Louis Vottero louis.vot@gmail.com    All rights reserved.
from __future__ import print_function
from __future__ import absolute_import

import os
import uuid
import math

from .. import rigs_maya
from .. import rigs_crossplatform
from .. import rigs
from ... import unreal_lib
from ...process_manager import process
from ... import util_math
from ... import util_file
from ... import util
from .. import util as util_ramen
from ... import qt_ui
from ... import qt
from ...util import StopWatch

from ... import logger

log = logger.get_logger(__name__)

in_maya = util.in_maya
if in_maya:
    import maya.cmds as cmds

in_unreal = util.in_unreal

uuids = {}


class ItemType(object):
    SOCKET = 1
    WIDGET = 2
    PROXY = 3
    LINE = 4
    NODE = 10001
    JOINTS = 10002
    COLOR = 10003
    CURVE_SHAPE = 10004
    TRANSFORM_VECTOR = 10005
    CONTROLS = 10005
    RIG = 20002
    FKRIG = 20003
    IKRIG = 20004
    GET_SUB_CONTROLS = 21000
    DATA = 30002
    PRINT = 30003
    UNREAL_SKELETAL_MESH = 30004


class SocketType(object):
    IN = 'in'
    OUT = 'out'
    TOP = 'top'


class NodeWindow(qt_ui.BasicGraphicsWindow):
    title = 'RAMEN'

    def __init__(self, parent=None):

        super(NodeWindow, self).__init__(parent)
        self.setWindowTitle('Ramen')

    def sizeHint(self):
        return qt.QtCore.QSize(800, 800)

    def _define_main_view(self):

        self.main_view_class = NodeViewDirectory()
        self.main_view = self.main_view_class.node_view

    def _build_widgets(self):

        self.side_menu = SideMenu()
        self.main_layout.addWidget(self.side_menu)

        self.side_menu.hide()


class NodeDirectoryWindow(NodeWindow):

    def __init__(self, parent=None):
        super(NodeDirectoryWindow, self).__init__(parent)
        self.directory = None

    def set_directory(self, directory):
        self.directory = directory
        self.main_view_class.set_directory(directory)


class NodeGraphicsView(qt_ui.BasicGraphicsView):

    def __init__(self, parent=None, base=None):
        super(NodeGraphicsView, self).__init__(parent)

        self.base = base

        self.prev_position = None
        self._cache = None
        self._zoom = 1
        self._zoom_min = 0.1
        self._zoom_max = 3.0

        self._cancel_context_popup = False
        self.drag = False
        self.right_click = False
        self.drag_accum = 0

        self.setRenderHints(qt.QPainter.Antialiasing |
                            qt.QPainter.HighQualityAntialiasing)

        brush = qt.QBrush()
        brush.setColor(qt.QColor(15, 15, 15, 1))
        self.setBackgroundBrush(brush)

        self.setFocusPolicy(qt.QtCore.Qt.StrongFocus)

        self.setHorizontalScrollBarPolicy(qt.QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(qt.QtCore.Qt.ScrollBarAlwaysOff)

    def drawBackground(self, painter, rect):

        size = 40

        pixmap = qt.QPixmap(size, size)
        pixmap.fill(qt.QtCore.Qt.transparent)

        pix_painter = qt.QPainter(pixmap)
        pix_painter.setBrush(qt.QColor.fromRgbF(.15, .15, .15, 1))

        pen = qt.QPen()
        pen.setStyle(qt.Qt.NoPen)
        pix_painter.setPen(pen)
        pix_painter.drawRect(0, 0, size, size)

        pen = qt.QPen()
        pen.setColor(qt.QColor.fromRgbF(0, 0, 0, .6))
        pen.setStyle(qt.Qt.SolidLine)

        middle = size * .5

        if self._zoom >= 2.5:
            pen.setWidth(1.5)
            pix_painter.setPen(pen)

            offset = 2

            pix_painter.drawLine(middle - offset, middle, middle + offset, middle)
            pix_painter.drawLine(middle, middle - offset, middle, middle + offset)

        if self._zoom >= .75 and self._zoom < 2.5:
            pen.setWidth(3)
            pix_painter.setPen(pen)
            pix_painter.drawPoint(qt.QtCore.QPointF(middle, middle))

        pix_painter.end()

        painter.fillRect(rect, pixmap)

    def _define_main_scene(self):

        if hasattr(self, 'main_scene') and self.main_scene:
            self.main_scene.clear()

        self.main_scene = NodeScene()

        self.main_scene.setObjectName('main_scene')

        self.setScene(self.main_scene)

        # small scene size helps the panning
        self.main_scene.setSceneRect(0, 0, 1, 1)

        self.setResizeAnchor(self.AnchorViewCenter)

    def keyPressEvent(self, event):

        items = self.main_scene.selectedItems()
        """
        if event.key() == qt.Qt.Key_F:


            position = items[0].pos()
            #position = self.mapToScene(items[0].pos())
            self.centerOn(position)
        """
        if event.key() == qt.Qt.Key_Delete:
            for item in items:
                item.base.delete()

        super(NodeGraphicsView, self).keyPressEvent(event)

    def wheelEvent(self, event):
        """
        Zooms the QGraphicsView in/out.

        """

        mouse_pos = event.pos()

        item = self.itemAt(mouse_pos)
        item_string = str(item)

        if item_string.find('widget=QComboBoxPrivateContainer') > -1:
            super(NodeGraphicsView, self).wheelEvent(event)
            return

        else:
            in_factor = .85
            out_factor = 1.0 / in_factor
            mouse_pos = event.pos() * 1.0
            old_pos = self.mapToScene(mouse_pos)
            zoom_factor = None
            if event.delta() < 0:
                zoom_factor = in_factor
            if event.delta() > 0:
                zoom_factor = out_factor
            if event.delta() == 0:
                return

            self._zoom *= zoom_factor

            if self._zoom <= self._zoom_min:
                self._zoom = self._zoom_min

            if self._zoom >= self._zoom_max:
                self._zoom = self._zoom_max

            self.setTransform(qt.QTransform().scale(self._zoom, self._zoom))

            new_pos = self.mapToScene(event.pos())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())

    def mousePressEvent(self, event):
        if event.button() == qt.QtCore.Qt.MiddleButton or event.button() == qt.QtCore.Qt.RightButton:
            self.setDragMode(qt.QGraphicsView.NoDrag)
            self.drag = True
            self.prev_position = event.pos()

        if event.button() == qt.QtCore.Qt.RightButton:
            self.right_click = True

        elif event.button() == qt.QtCore.Qt.LeftButton:
            self.setDragMode(qt.QGraphicsView.RubberBandDrag)

            super(NodeGraphicsView, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super(NodeGraphicsView, self).mouseMoveEvent(event)
        if self.drag:
            self.setCursor(qt.QtCore.Qt.SizeAllCursor)
            offset = self.prev_position - event.pos()

            distance = util_math.get_distance_2D([self.prev_position.x(), self.prev_position.y()],
                                                 [event.pos().x(), event.pos().y()])
            self.drag_accum += distance
            self.prev_position = event.pos()

            transform = self.transform()
            offset_x = offset.x() / transform.m11()
            offset_y = offset.y() / transform.m22()
            self.main_scene.setSceneRect(self.main_scene.sceneRect().translated(offset_x, offset_y))

            return

    def mouseReleaseEvent(self, event):

        if self.drag:
            self.drag = False

            self.setCursor(qt.QtCore.Qt.ArrowCursor)
            self.setDragMode(qt.QGraphicsView.RubberBandDrag)

        super(NodeGraphicsView, self).mouseReleaseEvent(event)

        if self.right_click:

            if abs(self.drag_accum) > 30:
                self._cancel_context_popup = True
            #    self._build_context_menu(event)

            self.right_click = False
            self.drag_accum = 0

    def contextMenuEvent(self, event):
        super(NodeGraphicsView, self).contextMenuEvent(event)

        if self._cancel_context_popup:
            self._cancel_context_popup = False
            return

        if not event.isAccepted():
            self._build_context_menu(event)

    def _build_context_menu(self, event):

        self.menu = qt.QMenu()

        item_action_dict = {}

        self.store_action = qt.QAction('Save', self.menu)
        self.rebuild_action = qt.QAction('Open', self.menu)
        self.menu.addAction(self.store_action)
        self.menu.addAction(self.rebuild_action)

        self.menu.addSeparator()

        for node_number in register_item:
            node_name = register_item[node_number].item_name

            item_action = qt.QAction(node_name, self.menu)
            self.menu.addAction(item_action)

            item_action_dict[item_action] = node_number

        self.menu.addSeparator()

        action = self.menu.exec_(event.globalPos())

        pos = event.pos()
        pos = self.mapToScene(pos)

        if action in item_action_dict:
            node_number = item_action_dict[action]
            self.base.add_rig_item(node_number, pos)

        if action == self.store_action:
            self.base.save()

        if action == self.rebuild_action:
            self.base.open()


class NodeView(object):

    def __init__(self):

        if not qt.is_batch():
            self.node_view = NodeGraphicsView(base=self)
        else:
            self.node_view = None

        self.items = []

        self._scene_signals()

    def _scene_signals(self):
        if not self.node_view:
            return

        self.node_view.main_scene.node_connect.connect(self._node_connected)
        self.node_view.main_scene.node_disconnect.connect(self._node_disconnected)
        self.node_view.main_scene.node_selected.connect(self._node_selected)
        self.node_view.main_scene.node_deleted.connect(self._node_deleted)

    def _node_connected(self, line_item):

        source_socket = line_item.source
        target_socket = line_item.target
        connect_socket(source_socket, target_socket)

        # exec_string = 'node_item._rig.%s = %s' % (socket_item.name, socket_item.value)
        # exec(exec_string, {'node_item':node_item})

    def _node_disconnected(self, source_socket, target_socket):
        disconnect_socket(target_socket)

    def _node_selected(self, node_items):
        pass
        """
        if node_items:
            self.side_menu.show()
            self.side_menu.nodes = node_items
        else:
            self.side_menu.hide()
            self.side_menu.nodes = []
        """

    def _node_deleted(self, node_items):

        for node in node_items:
            if hasattr(node, '_rig'):
                node._rig.delete()

    def clear(self):
        self.items = []
        if self.node_view:
            self.node_view.main_scene.clear()

    def save(self):

        log.info('Save Nodes')

        found = []

        items = self.items

        for item in items:

            if not hasattr(item, 'item_type'):
                continue

            if item.item_type < ItemType.NODE:
                if item.item_type != ItemType.LINE:
                    continue
            item_dict = item.store()

            found.append(item_dict)

        self._cache = found

        return found

    def open(self):

        watch = util.StopWatch()
        watch.start('Opening Graph')

        if not self._cache:
            watch.end()
            return

        item_dicts = self._cache

        self.clear()

        lines = []

        for item_dict in item_dicts:
            type_value = item_dict['type']
            if type_value == ItemType.LINE:
                lines.append(item_dict)
            if type_value >= ItemType.NODE:
                self._build_rig_item(item_dict)

        for line in lines:
            self._build_line(line)

        util.show('%s items loaded' % len(item_dicts))
        watch.end()

    def _build_rig_item(self, item_dict):
        type_value = item_dict['type']
        uuid_value = item_dict['uuid']
        item_inst = register_item[type_value](uuid_value=uuid_value)

        uuids[uuid_value] = item_inst

        item_inst.load(item_dict)

        if item_inst:
            self.add_item(item_inst)

            if self.node_view:
                item_inst.graphic.setZValue(item_inst.graphic._z_value)

    def _build_line(self, item_dict):
        line_inst = NodeLine()
        line_inst.load(item_dict)

        self.add_item(line_inst)

    def add_item(self, item_inst):
        self.items.append(item_inst)
        if self.node_view:
            if hasattr(item_inst, 'graphic'):
                self.node_view.main_scene.addItem(item_inst.graphic)
            else:
                self.node_view.main_scene.addItem(item_inst)

    def add_rig_item(self, node_type, position):

        if node_type in register_item:
            item_inst = register_item[node_type]()

            self.add_item(item_inst)
            if self.node_view:
                item_inst.graphic.setPos(position)
                item_inst.graphic.setZValue(item_inst.graphic._z_value)


class NodeViewDirectory(NodeView):

    def set_directory(self, directory):

        self._cache = None
        self.directory = directory

        self.clear()
        self.open()

    def get_file(self):

        if not hasattr(self, 'directory'):
            return

        if not util_file.exists(self.directory):
            util_file.create_dir(self.directory)

        path = os.path.join(self.directory, 'ramen.json')

        return path

    def save(self):
        result = super(NodeViewDirectory, self).save()

        filepath = self.get_file()

        util_file.set_json(filepath, self._cache, append=False)

        util.show('Saved Ramen to: %s' % filepath)

        return filepath

    def open(self):
        self.node_view.main_scene.clear()
        filepath = self.get_file()
        if filepath and util_file.exists(filepath):
            self._cache = util_file.get_json(filepath)
        util.show('Loading %s' % filepath)
        super(NodeViewDirectory, self).open()


class NodeScene(qt.QGraphicsScene):
    node_disconnect = qt.create_signal(object, object)
    node_connect = qt.create_signal(object)
    node_selected = qt.create_signal(object)
    node_deleted = qt.create_signal(object)

    def __init__(self):
        super(NodeScene, self).__init__()
        self.selection = None
        self.selectionChanged.connect(self._selection_changed)

    def mouseMoveEvent(self, event):
        super(NodeScene, self).mouseMoveEvent(event)

        if not self.selection or len(self.selection) == 1:
            return

        if not event.buttons() == qt.QtCore.Qt.LeftButton:
            return

        for item in self.selection:

            item = item.base

            sockets = item.get_all_sockets()

            visited = {}

            for socket_name in sockets:
                socket = sockets[socket_name]
                if socket_name in visited:
                    continue
                if hasattr(socket, 'lines'):
                    for line in socket.lines:
                        if line.source and line.target:
                            line.graphic.point_a = line.source.graphic.get_center()
                            line.graphic.point_b = line.target.graphic.get_center()

                visited[socket_name] = None

    def _selection_changed(self):

        items = self.selectedItems()

        if items:
            self.selection = items
        else:
            self.selection = []

        self.node_selected.emit(items)


class SideMenu(qt.QFrame):

    def __init__(self, parent=None):
        super(SideMenu, self).__init__(parent)
        self.setObjectName('side_menu')
        self._build_widgets()

        self._items = []
        self._group_widgets = []

    def _build_widgets(self):
        # Frame.
        self.setFixedWidth(200)

        self.main_layout = qt.QVBoxLayout(self)
        self.main_layout.setAlignment(qt.Qt.AlignCenter)

    def _clear_widgets(self):
        for widget in self._group_widgets:
            self.main_layout.removeWidget(widget)
            widget.deleteLater()

        self._group_widgets = []

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, items):
        self._items = items

        self._clear_widgets()

        for item in self._items:
            name = item.name

            group = qt_ui.Group(name)
            self.main_layout.addWidget(group)
            self._group_widgets.append(group)

            if hasattr(item, '_rig'):

                rig_class = item._rig
                node_attributes = rig_class.get_node_attributes()

                for attribute in node_attributes:

                    value, attr_type = rig_class.get_node_attribute(attribute)

                    if attr_type == rigs.AttrType.STRING:
                        string_attr = qt_ui.GetString(attribute)
                        string_attr.set_text(value)
                        group.main_layout.addWidget(string_attr)

#--- Attributes


class AttributeItem(object):
    item_type = None

    name = None
    value = None
    data_type = None

    def __init__(self, graphic=None):

        self._name = None
        self._value = None
        self._data_type = None
        self.graphic = graphic
        if self.graphic:
            self.graphic.base = self
        self.parent = None

    def _get_value(self):
        if self.graphic:
            self._value = self.graphic.get_value()

        return self._value

    def _set_value(self, value):

        self._value = value

        if self.graphic:
            self.graphic.set_value(value)

    def _set_name(self, name):
        self._name = name
        if self.graphic:
            self.graphic.set_name(name)

    @property
    def value(self):
        return self._get_value()

    @value.setter
    def value(self, value):
        if hasattr(self, 'blockSignals'):
            self.blockSignals(True)

        self._set_value(value)

        if hasattr(self, 'blockSignals'):
            self.blockSignals(False)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._set_name(name)

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, data_type):
        self._data_type = data_type

    def set_graphic(self, item_inst):
        if not qt.is_batch():
            self.graphic = item_inst
            self.graphic.base = self

    def store(self):

        item_dict = {}
        if self.graphic:
            self.item_type = self.graphic.item_type
        else:
            item_dict['type'] = self.item_type

        return item_dict

    def load(self, item_dict):
        pass

    def set_parent(self, parent_item):
        if hasattr(parent_item, 'base'):
            parent_item = parent_item.base

        self.parent = parent_item

        if self.graphic:
            self.graphic.setParentItem(parent_item.graphic)

            if hasattr(parent_item.graphic, 'node_width'):
                self.graphic.node_width = parent_item.graphic.node_width

    def get_parent(self):
        return self.parent
        """
        if not self.graphic:
            return

        return self.graphic.parentItem().base
        """


class AttributeGraphicItem(qt.QGraphicsObject):
    item_type = ItemType.WIDGET
    changed = qt.create_signal(object, object)

    def __init__(self, parent=None, width=80, height=16):
        self.base = None
        self.value = None
        self.name = None
        super(AttributeGraphicItem, self).__init__(parent)

    def _convert_to_nicename(self, name):

        name = name.replace('_', ' ')
        name = name.title()

        return name

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def set_name(self, name):
        self.name = name


class GraphicTextItem(qt.QGraphicsTextItem):

    edit = qt.create_signal(object)
    before_text_changed = qt.create_signal()
    after_text_changed = qt.create_signal()
    enter_pressed = qt.create_signal()

    def __init__(self, text=None, parent=None, rect=None):
        super(GraphicTextItem, self).__init__(text, parent)
        self.rect = rect
        self.setFlag(self.ItemIsSelectable, False)
        self.setFlag(self.ItemIsFocusable, True)

        self.setDefaultTextColor(qt.QColor(160, 160, 160, 255))
        self.limit = True
        self.setTabChangesFocus(True)

    def boundingRect(self):

        if self.limit:
            return self.rect
        else:
            rect = super(GraphicTextItem, self).boundingRect()
            return rect

    def mousePressEvent(self, event):
        super(GraphicTextItem, self).mousePressEvent(event)
        self.edit.emit(True)
        self.limit = False

    def focusOutEvent(self, event):
        super(GraphicTextItem, self).focusOutEvent(event)
        self.edit.emit(False)
        self.limit = True

    def paint(self, painter, option, widget):
        option.state = qt.QStyle.State_None
        super(GraphicTextItem, self).paint(painter, option, widget)

    def keyPressEvent(self, event):
        self.limit = False
        self.before_text_changed.emit()

        if event.key() == qt.QtCore.Qt.Key_Return:
            self.enter_pressed.emit()
            self.edit.emit(False)
        else:
            super(GraphicTextItem, self).keyPressEvent(event)
        self.after_text_changed.emit()


class CompletionTextItem(GraphicTextItem):

    text_clicked = qt.create_signal(object)

    def mousePressEvent(self, event):
        super(CompletionTextItem, self).mousePressEvent(event)
        position = event.pos()

        pos_y = position.y() - self.pos().y()
        if pos_y < 1:
            return
        line_height = 13  # line_height = block.layout().boundingRect().height()
        part = pos_y / line_height
        section = math.floor(part)

        block = self.document().findBlockByLineNumber(section)

        self.edit.emit(True)
        self.limit = False

        self.text_clicked.emit(block.text())


class GraphicNumberItem(GraphicTextItem):

    tab_pressed = qt.create_signal()

    def __init__(self, text=None, parent=None, rect=None):
        super(GraphicNumberItem, self).__init__(text, parent, rect)

        self.setDefaultTextColor(qt.QColor(0, 0, 0, 255))

    def keyPressEvent(self, event):
        self.before_text_changed.emit()

        accept_text = True
        text = event.text()

        if event.key() == qt.QtCore.Qt.Key_Return:
            self.enter_pressed.emit()
            accept_text = False
        elif not self._is_text_acceptable(text):
            accept_text = False

        if accept_text:
            super(GraphicNumberItem, self).keyPressEvent(event)

        self.after_text_changed.emit()

    def _is_text_acceptable(self, text):
        full_text = self.toPlainText()

        if text == '.' and full_text.find('.') > -1:
            selected_text = self.textCursor().selectedText()
            if selected_text.find('.') > -1:
                return True

            return False
        elif text.isalpha():
            return False
        else:
            return True

    def event(self, event):

        if event.type() == qt.QtCore.QEvent.KeyPress and event.key() == qt.QtCore.Qt.Key_Tab:
            self.tab_pressed.emit()
            self.edit.emit(False)
            self.limit = True

        return super(GraphicNumberItem, self).event(event)


class StringItem(AttributeGraphicItem):
    item_type = ItemType.WIDGET
    edit = qt.create_signal(object)
    changed = qt.create_signal(object, object)

    def __init__(self, parent=None, width=80, height=16):
        super(StringItem, self).__init__()
        self.setParentItem(parent)
        self.width = width
        self.height = height
        self.limit = True
        self._text_pixel_size = 12
        self._background_color = qt.QColor(30, 30, 30, 255)
        self._edit_mode = False
        self._completion_examples = []
        self._completion_examples_current = []

        self.rect = qt.QtCore.QRect(10, 2, self.width, self.height)
        text_rect = qt.QtCore.QRect(0, self.rect.y(), self.width, self.height)
        self.text_rect = text_rect
        self.text_item = None
        self._build_items()
        self._init_paint()
        self._paint_base_text = True

    def _build_items(self):
        self.place_holder = ''
        self._using_placeholder = True

        self.text_item = self._define_text_item()
        self.text_item.setTextWidth(self.width)
        self.text_item.edit.connect(self._edit)

        self.text_item.setPos(10, -2)
        self.text_item.setFlag(self.ItemClipsToShape)

        self.text_item.setFlag(self.ItemIsFocusable)
        self.text_item.setTextInteractionFlags(qt.QtCore.Qt.TextEditable)
        self.text_item.setParentItem(self)
        self.text_item.before_text_changed.connect(self._before_text_changed)
        self.text_item.after_text_changed.connect(self._after_text_changed)
        self.text_item.enter_pressed.connect(self._enter_pressed)

        self.completion_text_item = CompletionTextItem(rect=self.text_rect)
        self.completion_text_item.hide()
        self.completion_text_item.setParentItem(self)
        self.completion_text_item.setPos(15, 5)
        self.completion_text_item.text_clicked.connect(self._update_text)

    def _init_paint(self):
        self.font = qt.QFont()
        self.font.setPixelSize(self._text_pixel_size)
        # self.font.setBold(True)

        if self.text_item:
            self.text_item.setFont(self.font)

        # Brush.
        self.brush = qt.QBrush()
        self.brush.setStyle(qt.QtCore.Qt.SolidPattern)
        self.brush.setColor(self._background_color)

        # Pen.
        self.pen = qt.QPen()
        self.pen.setStyle(qt.QtCore.Qt.SolidLine)
        self.pen.setWidth(.5)
        self.pen.setColor(qt.QColor(90, 90, 90, 255))

    def _define_text_item(self):
        return GraphicTextItem(rect=self.text_rect)

    def _define_text_color(self):
        return qt.QColor(160, 160, 160, 255)

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        # TODO refactor into smaller functions
        self.brush.setColor(self._background_color)
        self.font.setPixelSize(self._text_pixel_size)
        if not self._paint_base_text:
            return
        if self._using_placeholder:
            self.text_item.setDefaultTextColor(qt.QColor(80, 80, 80, 255))
        else:
            self.text_item.setDefaultTextColor(self._define_text_color())

        painter.setBrush(self.brush)
        painter.setFont(self.font)
        painter.setPen(self.pen)

        size_value = self.text_item.document().size()

        if self.text_item.limit:
            rect = self.rect
        else:

            width = self.rect.width() * 1.3

            rect = qt.QtCore.QRect(10,
                                   0,
                                   width,
                                   size_value.height())
            if self.text_item:
                self.text_item.setTextWidth(width)

        painter.drawRoundedRect(rect, 0, 0)

        if not self._edit_mode:
            self.completion_text_item.hide()
            self._completion_examples_current = []
            return

        if self._completion_examples_current:
            self.completion_text_item.show()
            text = ''
            for example in self._completion_examples_current:
                text += '\n%s' % example

            self.completion_text_item.setPlainText(text)

            size_value = self.completion_text_item.document().size()
            width = self.rect.width() * 1.3
            height = size_value.height()
            if height > 200:
                height = 200
            rect = qt.QtCore.QRect(0,
                                   12,
                                   width,
                                   height)
            # self.completion_text_item.setTextWidth(width)
            self.completion_text_item.rect = rect

            rect = qt.QtCore.QRect(10,
                       self.height + 7,
                       width,
                       height + 7)

            painter.drawRoundedRect(rect, 0, 0)

        else:
            self.completion_text_item.hide()

    def _update_text(self, text):
        self.text_item.setPlainText(text)
        self._using_placeholder = False

    def _edit(self, bool_value):
        self._edit_mode = bool_value
        self.edit.emit(bool_value)
        parent = self.parentItem()
        parent.setSelected(False)

        if bool_value:
            self.limit = False

            if self._using_placeholder:
                self.text_item.setTextInteractionFlags(qt.QtCore.Qt.TextEditable)

                text_cursor = qt.QTextCursor(self.text_item.document())
                text_cursor.movePosition(qt.QTextCursor.Start)
                self.text_item.setTextCursor(text_cursor)
            else:
                self.text_item.setTextInteractionFlags(qt.QtCore.Qt.TextEditorInteraction)

        else:
            self.limit = True
            self.text_item.limit = True

    def _before_text_changed(self):

        current_text = self.text_item.toPlainText()
        if self._using_placeholder and current_text:
            self.text_item.setPlainText('')
            self._using_placeholder = False
            self.text_item.setTextInteractionFlags(qt.QtCore.Qt.TextEditorInteraction)

    def _after_text_changed(self):
        current_text = self.text_item.toPlainText()
        if not current_text and self.place_holder:
            self.text_item.setPlainText(self.place_holder)
            self._using_placeholder = True
            self.text_item.setTextInteractionFlags(qt.QtCore.Qt.TextEditable)

        if self._completion_examples:
            matches = []

            for example in self._completion_examples:
                found = False
                if example.find(current_text) > -1:
                    matches.append(example)
                    found = True
                if not found:
                    if example.find(current_text.title()) > -1:
                        matches.append(example)

            self._completion_examples_current = matches

    def _enter_pressed(self):
        self.limit = True
        if self.text_item:
            self.text_item.limit = True

        self._emit_change()

    def _emit_change(self):
        self.changed.emit(self.base.name, self.get_value())

    def set_background_color(self, qcolor):

        self._background_color = qcolor

    def set_text_pixel_size(self, pixel_size):
        self._text_pixel_size = pixel_size
        self.font.setPixelSize(self._text_pixel_size)

    def set_placeholder(self, text):
        self.place_holder = text

        if self._using_placeholder and self.place_holder:
            self.text_item.setPlainText(self.place_holder)

    def set_completion_examples(self, list_of_strings):
        self._completion_examples = list_of_strings

    def get_value(self):
        if self._using_placeholder:
            return ['']
        value = self.text_item.toPlainText()
        return [value]

    def set_value(self, value):

        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        if not value:
            self._using_placeholder = True
            if self.place_holder:
                self.text_item.setPlainText(self.place_holder)
            return

        self._using_placeholder = False

        self.text_item.setPlainText(str(value))

    def set_name(self, name):
        self.set_placeholder(self._convert_to_nicename(name))


class BoolGraphicItem(AttributeGraphicItem):
    item_type = ItemType.WIDGET
    changed = qt_ui.create_signal(object, object)

    def __init__(self, parent=None, width=15, height=15):
        self.value = None
        super(AttributeGraphicItem, self).__init__(parent)
        self.nice_name = ''

        self.rect = qt.QtCore.QRect(10, 0, width, height)
        # self.rect = qt.QtCore.QRect(10,10,50,20)

        self._init_paint()

    def _init_paint(self):
        # Brush.
        self.brush = qt.QBrush()
        self.brush.setStyle(qt.QtCore.Qt.SolidPattern)
        self.brush.setColor(qt.QColor(30, 30, 30, 255))

        # Pen.
        self.pen = qt.QPen()
        self.pen.setStyle(qt.QtCore.Qt.SolidLine)
        self.pen.setWidth(1)
        self.pen.setColor(qt.QColor(120, 120, 120, 255))

        self.selPen = qt.QPen()
        self.selPen.setStyle(qt.QtCore.Qt.SolidLine)
        self.selPen.setWidth(3)
        self.selPen.setColor(qt.QColor(255, 255, 255, 255))

        self.title_font = qt.QFont()
        self.title_font.setPixelSize(10)
        self.title_pen = qt.QPen()
        self.title_pen.setWidth(.5)
        self.title_pen.setColor(qt.QColor(200, 200, 200, 255))

        self.check_pen = qt.QPen()
        self.check_pen.setWidth(2)
        self.check_pen.setCapStyle(qt.QtCore.Qt.RoundCap)
        self.check_pen.setColor(qt.QColor(200, 200, 200, 255))

    def paint(self, painter, option, widget):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)

        painter.drawRoundedRect(self.rect, 5, 5)

        painter.setPen(self.title_pen)
        painter.setFont(self.title_font)
        painter.drawText(30, 12, self.nice_name)
        if self.value:
            painter.setPen(self.check_pen)
            line1 = qt.QtCore.QLine(self.rect.x() + 3,
                            self.rect.y() + 7,
                            self.rect.x() + 6,
                            self.rect.y() + 12)

            line2 = qt.QtCore.QLine(self.rect.x() + 6,
                            self.rect.y() + 12,
                            self.rect.x() + 12,
                            self.rect.y() + 4)

            painter.drawLines([line1, line2])

        # painter.drawRect(self.rect)

    def mousePressEvent(self, event):

        super(BoolGraphicItem, self).mousePressEvent(event)

        if self.value == 1:
            self.value = 0
        else:
            self.value = 1

        self.update()
        self.changed.emit(self.name, self.value)

    def boundingRect(self):
        return qt.QtCore.QRectF(self.rect)

    def get_value(self):
        value = super(BoolGraphicItem, self).get_value()
        return value

    def set_value(self, value):
        super(BoolGraphicItem, self).set_value(value)

    def set_name(self, name):
        super(BoolGraphicItem, self).set_name(name)
        self.nice_name = self._convert_to_nicename(name)


class IntGraphicItem(StringItem):

    def __init__(self, parent=None, width=50, height=14):
        super(IntGraphicItem, self).__init__(parent, width, height)
        if self.text_item:
            self.text_item.setTextInteractionFlags(qt.QtCore.Qt.TextEditorInteraction)
            # self.text_item.tab_pressed.connect(self._handle_tab)
        self._using_placeholder = False
        self._nice_name = None
        self._background_color = qt.QColor(100 * .8, 255 * .8, 220 * .8, 255)

    def _define_text_item(self):
        return GraphicNumberItem(rect=self.text_rect)

    def _define_text_color(self):
        return qt.QColor(60, 60, 60, 255)

    # def _handle_tab(self):
    #    print('number handle tab')
    #    text = self.text_item.toPlainText()
    #    print(repr(text))

    def _init_paint(self):
        self.font = qt.QFont()
        self.font.setPixelSize(12)
        self.font.setBold(True)

        # Brush.
        self.brush = qt.QBrush()
        self.brush.setStyle(qt.QtCore.Qt.SolidPattern)
        self.brush.setColor(self._background_color)

        # Pen.
        self.pen = qt.QPen()
        self.pen.setStyle(qt.QtCore.Qt.SolidLine)
        self.pen.setWidth(.5)
        self.pen.setColor(qt.QColor(90, 90, 90, 255))

        self.title_font = qt.QFont()
        self.title_font.setPixelSize(10)
        self.title_pen = qt.QPen()
        self.title_pen.setWidth(.5)
        self.title_pen.setColor(qt.QColor(200, 200, 200, 255))

    def paint(self, painter, option, widget):
        option.state = qt.QStyle.State_None
        if self._nice_name:
            painter.setPen(self.title_pen)
            painter.setFont(self.title_font)
            painter.drawText(self.width + 15, 15, self._nice_name)

        super(IntGraphicItem, self).paint(painter, option, widget)

    def _edit(self, bool_value):

        self._edit_mode = bool_value
        self.edit.emit(bool_value)
        parent = self.parentItem()
        parent.setSelected(False)

        if bool_value:
            self.limit = False
            self.text_item.setTextInteractionFlags(qt.QtCore.Qt.TextEditorInteraction)
            cursor = self.text_item.textCursor()
            cursor.select(qt.QTextCursor.Document)
            self.text_item.setTextCursor(cursor)

        else:
            self.limit = True
            self.text_item.limit = True

            cursor = self.text_item.textCursor()
            cursor.clearSelection()
            self.text_item.setTextCursor(cursor)
            self._emit_change()

    def _number_to_text(self, number):
        return str(int(number))

    def _text_to_number(self, text):
        number = 0
        if text:
            number = int(round(float(text), 0))

        return number

    def _current_text_to_number(self):

        if not self.text_item:
            return
        text = self.text_item.toPlainText()
        if text:
            number = self._text_to_number(text)
        else:
            number = 0

        return number

    def _enter_pressed(self):
        if self.text_item:
            number = self._current_text_to_number()
            self.text_item.setPlainText(str(number))
        super(IntGraphicItem, self)._enter_pressed()

    def _before_text_changed(self):
        return

    def _after_text_changed(self):
        return

    def get_value(self):
        value = self._current_text_to_number()
        return [value]

    def set_value(self, value):
        if value:
            value = value[0]

        if self.text_item:
            self.text_item.setPlainText(self._number_to_text(value))

    def set_name(self, name):
        super(IntGraphicItem, self).set_name(name)
        self._nice_name = self._convert_to_nicename(name)


class NumberGraphicItem(IntGraphicItem):

    def _text_to_number(self, text):
        number = 0.00
        if text:
            number = round(float(text), 3)

        return number

    def _number_to_text(self, number):
        return str(round(number, 3))

    def set_value(self, value):
        super(StringItem, self).set_value(value)
        if isinstance(value, float):
            value = [value]

        value = value[0]
        if self.text_item:
            self.text_item.setPlainText(self._number_to_text(value))


class VectorGraphicItem(NumberGraphicItem):

    def __init__(self, parent=None, width=100, height=14):
        super(NumberGraphicItem, self).__init__(parent, width, height)
        self._paint_base_text = False

    def _build_items(self):
        text_size = 8

        self.vector_x = AttributeItem()
        self.vector_x.set_graphic(NumberGraphicItem(self, 35))
        self.vector_x.graphic.setZValue(100)
        self.vector_x.graphic.set_background_color(qt.QColor(255 * .8, 200 * .8, 200 * .8, 255))

        self.vector_y = AttributeItem()
        self.vector_y.set_graphic(NumberGraphicItem(self, 35))
        self.vector_y.graphic.moveBy(35, 0)
        self.vector_y.graphic.setZValue(90)
        self.vector_y.graphic.set_background_color(qt.QColor(200 * .8, 255 * .8, 200 * .8, 255))

        self.vector_z = AttributeItem()
        self.vector_z.set_graphic(NumberGraphicItem(self, 35))
        self.vector_z.graphic.moveBy(70, 0)
        self.vector_z.graphic.setZValue(80)
        self.vector_z.graphic.set_background_color(qt.QColor(200 * .8, 200 * .8, 255 * .8, 255))

        # self.vector_x.edit.connect(self._handle_edit_x)
        # self.vector_y.edit.connect(self._handle_edit_y)
        # self.vector_z.edit.connect(self._handle_edit_z)

        self.vector_x.graphic.changed.connect(self._emit_vector_change)
        self.vector_y.graphic.changed.connect(self._emit_vector_change)
        self.vector_z.graphic.changed.connect(self._emit_vector_change)

        self.numbers = [self.vector_x, self.vector_y, self.vector_z]

        for vector in self.numbers:
            vector.graphic.set_text_pixel_size(text_size)

        # self.vector_x.text_item.tab_pressed.connect(self._handle_tab_x)
        # self.vector_y.text_item.tab_pressed.connect(self._handle_tab_y)
        # self.vector_z.text_item.tab_pressed.connect(self._handle_tab_z)

    def _handle_edit_x(self, bool_value):
        print('edit x', bool_value)

    def _handle_edit_y(self, bool_value):
        print('edit y', bool_value)

    def _handle_edit_z(self, bool_value):
        print('edit z', bool_value)

    def _handle_tab_x(self):

        print('tab on x')

        self.vector_y.graphic.limit = False
        self.vector_y.graphic.text_item.limit = False

        print('done setting foxus')
        """
        self.vector_x._edit(False)
        self.vector_x.text_item.limit = True
        self.vector_z._edit(False)
        self.vector_z.text_item.limit = True

        self.vector_y.text_item.setActive(True)
        
        self.vector_y.text_item.grabKeyboard()
        self.vector_y._edit(True)
        self.vector_y.text_item.limit = False
        """
        print('end tab x')

    def _handle_tab_y(self):

        print('tab on y')
        # self.vector_y.limit = False
        self.vector_y.graphic._edit(False)
        self.vector_y.graphic.text_item.limit = True
        self.vector_x.graphic._edit(False)
        self.vector_x.graphic.text_item.limit = True

        self.vector_z.graphic._edit(True)
        self.vector_z.graphic.text_item.limit = False

    def _handle_tab_z(self):

        print('tab on z')
        # self.vector_y.limit = False
        self.vector_z.graphic._edit(False)
        self.vector_z.graphic.text_item.limit = True
        self.vector_y.graphic._edit(False)
        self.vector_y.graphic.text_item.limit = True

        self.vector_x.graphic._edit(True)
        self.vector_x.graphic.text_item.limit = False
        self.vector_x.graphic.text_item.setFlag(qt.QGraphicsTextItem.ItemIsFocusable)
        self.vector_x.graphic.setFocus()

    def _emit_vector_change(self):

        self._emit_change()

    def _init_paint(self):
        super(VectorGraphicItem, self)._init_paint()
        self.title_font = qt.QFont()
        self.title_font.setPixelSize(8)

    def get_value(self):
        value_x = self.numbers[0].value[0]
        value_y = self.numbers[1].value[0]
        value_z = self.numbers[2].value[0]

        return [(value_x, value_y, value_z)]

    def set_value(self, value):
        self.numbers[0].value = value[0][0]
        self.numbers[1].value = value[0][1]
        self.numbers[2].value = value[0][2]


class ColorPickerItem(AttributeGraphicItem):
    item_type = ItemType.WIDGET
    changed = qt_ui.create_signal(object, object)

    def __init__(self, parent=None, width=40, height=14):
        super(ColorPickerItem, self).__init__(parent)
        self._name = 'color'

        self.rect = qt.QtCore.QRect(10, 15, width, height)
        # self.rect = qt.QtCore.QRect(10,10,50,20)

        self._init_paint()

    def _init_paint(self):
        # Brush.
        self.brush = qt.QBrush()
        self.brush.setStyle(qt.QtCore.Qt.SolidPattern)
        self.brush.setColor(qt.QColor(90, 90, 90, 255))

        # Pen.
        self.pen = qt.QPen()
        self.pen.setStyle(qt.QtCore.Qt.SolidLine)
        self.pen.setWidth(1)
        self.pen.setColor(qt.QColor(20, 20, 20, 255))

        self.selPen = qt.QPen()
        self.selPen.setStyle(qt.QtCore.Qt.SolidLine)
        self.selPen.setWidth(3)
        self.selPen.setColor(qt.QColor(255, 255, 255, 255))

    def paint(self, painter, option, widget):
        painter.setBrush(self.brush)
        if self.isSelected():
            painter.setPen(self.selPen)
        else:
            painter.setPen(self.pen)

        painter.drawRoundedRect(self.rect, 5, 5)

    def mousePressEvent(self, event):

        super(ColorPickerItem, self).mousePressEvent(event)

        color_dialog = qt.QColorDialog
        color = color_dialog.getColor()

        if not color.isValid():
            return

        self.brush.setColor(color)
        self.update()

        self.changed.emit(self.name, self.get_value())

    def boundingRect(self):
        return qt.QtCore.QRectF(self.rect)

    def get_value(self):
        color = self.brush.color()
        color_value = color.getRgbF()
        color_value = [color_value[0], color_value[1], color_value[2], 1.0]
        return [color_value]

    def set_value(self, value):
        if not value:
            return
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        color = qt.QColor()
        color.setRgbF(value[0], value[1], value[2], 1.0)
        self.brush.setColor(color)


class TitleItem(AttributeGraphicItem):

    item_type = ItemType.WIDGET

    def __init__(self, parent=None):
        super(TitleItem, self).__init__(parent)

        self.rect = qt.QtCore.QRect(0, 0, 150, 20)
        # self.rect = qt.QtCore.QRect(10,10,50,20)

        self.font = qt.QFont()
        self.font.setPixelSize(10)
        self.font.setBold(True)

        self.font_metrics = qt.QFontMetrics(self.font)

        # Brush.
        self.brush = qt.QBrush()
        self.brush.setStyle(qt.QtCore.Qt.SolidPattern)
        self.brush.setColor(qt.QColor(60, 60, 60, 255))

        # Pen.
        self.pen = qt.QPen()
        self.pen.setStyle(qt.QtCore.Qt.DotLine)
        self.pen.setWidth(.5)
        self.pen.setColor(qt.QColor(200, 200, 200, 255))

    def paint(self, painter, option, widget):
        painter.setBrush(self.brush)
        painter.setFont(self.font)
        painter.setPen(self.pen)

        bounding_rect = self.font_metrics.boundingRect(self.name)

        painter.drawText(6, 13, self.name)

        parent_item = self.parentItem()
        rect = parent_item.boundingRect()
        painter.drawLine(bounding_rect.width() + 15, 10, rect.width() - 20, 10)

    def boundingRect(self):
        return qt.QtCore.QRectF(self.rect)

#--- Sockets


class NodeSocketItem(AttributeGraphicItem):

    def __init__(self, base=None):
        super(NodeSocketItem, self).__init__()
        self.base = base
        self.new_line = None
        self.color = None
        self.rect = None
        self.side_socket_height = None
        self.pen = None
        self.brush = None
        self.node_width = None

        self.init_socket(self.base.socket_type, self.base.data_type)

        self.font = qt.QFont()
        self.font.setPixelSize(10)

        self.get_nice_name()

    def get_nice_name(self):

        name = self.base._name

        if name:
            split_name = name.split('_')
            if split_name:
                found = []
                for name in split_name:
                    name = name.title()
                    found.append(name)
                self.nice_name = ' '.join(found)
            else:
                self.nice_name = name.title()
        else:
            self.nice_name = None

    def init_socket(self, socket_type, data_type):
        self.node_width = 150
        self.rect = qt.QtCore.QRectF(0.0, 0.0, 0.0, 0.0)

        self.side_socket_height = 0

        # Brush.
        self.brush = qt.QBrush()
        self.brush.setStyle(qt.QtCore.Qt.SolidPattern)
        self.brush.setColor(qt.QColor(60, 60, 60, 255))

        # Pen.
        self.pen = qt.QPen()

        self.color = qt.QColor(60, 60, 60, 255)

        self.pen.setColor(qt.QColor(200, 200, 200, 255))

        if data_type == rigs.AttrType.TRANSFORM:
            self.color = qt.QColor(100, 200, 100, 255)
        if data_type == rigs.AttrType.STRING:
            self.color = qt.QColor(100, 150, 220, 255)
        if data_type == rigs.AttrType.COLOR:
            self.color = qt.QColor(220, 150, 100, 255)
        if data_type == rigs.AttrType.VECTOR:
            self.color = qt.QColor(170, 70, 160, 255)
        self.brush.setColor(self.color)

        if socket_type == SocketType.IN:
            self.rect = qt.QtCore.QRect(-10.0, self.side_socket_height, 20.0, 20.0)

        if socket_type == SocketType.OUT:
            self.rect = qt.QtCore.QRect(self.node_width + 23, 5, 20.0, 20.0)

        if socket_type == SocketType.TOP:
            self.rect = qt.QtCore.QRect(10.0, -10.0, 15.0, 15.0)

    def boundingRect(self):
        return qt.QtCore.QRectF(self.rect)

    def paint(self, painter, option, widget):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        self.pen.setStyle(qt.QtCore.Qt.NoPen)
        self.pen.setWidth(0)
        painter.setPen(self.pen)

        painter.setFont(self.font)

        if self.base.socket_type == SocketType.IN:

            rect = qt.QtCore.QRectF(self.rect)
            rect.adjust(3.0, 3.0, -3.0, -3.0)
            painter.drawEllipse(rect)

            self.pen.setStyle(qt.QtCore.Qt.SolidLine)
            self.pen.setWidth(1)
            painter.setPen(self.pen)

            if self.base._data_type == rigs.AttrType.STRING:
                pass
            elif self.base._data_type == rigs.AttrType.VECTOR:
                pass
            elif self.base._data_type == rigs.AttrType.COLOR:
                painter.drawText(qt.QtCore.QPoint(55, self.side_socket_height + 14), self.nice_name)
            else:
                painter.drawText(qt.QtCore.QPoint(15, self.side_socket_height + 14), self.nice_name)

        if self.base.socket_type == SocketType.OUT:

            parent = self.get_parent()
            if parent:
                self.node_width = parent.graphic.node_width

            self.rect.setX(self.node_width)

            poly = qt.QPolygon()

            poly.append(qt.QtCore.QPoint(0, 3))
            poly.append(qt.QtCore.QPoint(0, 17))
            poly.append(qt.QtCore.QPoint(6, 17))

            poly.append(qt.QtCore.QPoint(14, 12))
            poly.append(qt.QtCore.QPoint(15, 10))
            poly.append(qt.QtCore.QPoint(14, 8))

            poly.append(qt.QtCore.QPoint(6, 3))

            poly.translate(self.rect.x(), self.rect.y())
            painter.drawPolygon(poly)

            self.pen.setStyle(qt.QtCore.Qt.SolidLine)
            self.pen.setWidth(1)
            painter.setPen(self.pen)
            name_len = painter.fontMetrics().width(self.nice_name)
            offset = self.node_width - 10 - name_len

            painter.drawText(qt.QtCore.QPoint(offset, self.side_socket_height + 17), self.nice_name)

        if self.base.socket_type == SocketType.TOP:
            rect = qt.QtCore.QRectF(self.rect)
            painter.drawRect(rect)

            self.pen.setStyle(qt.QtCore.Qt.SolidLine)
            self.pen.setWidth(1)
            painter.setPen(self.pen)

    def mousePressEvent(self, event):

        self.new_line = None

        if self.base.socket_type == SocketType.OUT:
            point_a = self.get_center()

            point_b = self.mapToScene(event.pos())
            self.new_line = NodeLine(point_a, point_b)

        elif self.base.socket_type == SocketType.IN:

            point_a = self.mapToScene(event.pos())
            point_b = self.get_center()

            self.new_line = NodeLine(point_a, point_b)

        else:
            super(NodeSocketItem, self).mousePressEvent(event)

        if self.new_line:
            self.base.lines.append(self.new_line)
            # self.scene().addItem(self.new_line.graphic)
            views = self.scene().views()
            for view in views:
                view.base.add_item(self.new_line)
            self.new_line.graphic.color = self.color

    def mouseMoveEvent(self, event):
        if self.base.socket_type == SocketType.OUT:
            point_b = self.mapToScene(event.pos())
            self.new_line.graphic.point_b = point_b
        elif self.base.socket_type == SocketType.IN:
            point_a = self.mapToScene(event.pos())
            self.new_line.graphic.point_a = point_a
        else:
            super(NodeSocketItem, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.new_line.graphic.hide()

        graphic = self.scene().itemAt(event.scenePos().toPoint(), qt.QTransform())

        if not graphic:
            return

        item = graphic.base

        self.new_line.graphic.show()

        connection_fail = False
        if item:
            if not hasattr(item, 'data_type'):
                self.base.remove_line(self.new_line)
                self.new_line = None
                return

            item_socket_type = None
            if hasattr(graphic, 'base'):
                if hasattr(graphic.base, 'socket_type'):
                    item_socket_type = graphic.base.socket_type

            if item == self.get_parent():
                connection_fail = 'Same node'

            if self.base.data_type != item.data_type:

                if self.socket_type == SocketType.IN and not self.base.data_type == rigs.AttrType.ANY:
                    connection_fail = 'Different Type'

                if item.socket_type == SocketType.IN and not item.data_type == rigs.AttrType.ANY:
                    connection_fail = 'Different Type'

        if connection_fail:
            self.base.remove_line(self.new_line)
            self.new_line = None
            util.warning('Cannot connect sockets: %s' % connection_fail)
            return

        if not item:
            self.base.remove_line(self.new_line)
            self.new_line = None
            return

        socket_type = self.base.socket_type

        if item == self.new_line or not item_socket_type:
            self.base.remove_line(self.new_line)
            self.new_line = None
            return
        if socket_type == item_socket_type:
            self.base.remove_line(self.new_line)
            self.new_line = None
            return
        if socket_type == SocketType.OUT and item_socket_type == SocketType.IN:
            self.new_line.source = self.base
            self.new_line.target = item
            self.new_line.graphic.point_b = item.graphic.get_center()

        elif socket_type == SocketType.OUT and item_socket_type == SocketType.TOP:
            self.new_line.source = self.base
            self.new_line.target = item
            self.new_line.graphic.point_b = item.graphic.get_center()

        elif socket_type == SocketType.TOP and item_socket_type == SocketType.OUT:
            self.new_line.source = item
            self.new_line.target = self.base
            self.new_line.graphic.point_a = item.graphic.get_center()

        elif socket_type == SocketType.IN and item_socket_type == SocketType.OUT:
            self.new_line.source = item
            self.new_line.target = self.base
            self.new_line.graphic.point_a = item.graphic.get_center()

        else:
            super(NodeSocketItem, self).mouseReleaseEvent(event)

        if self.new_line:
            self.scene().node_connect.emit(self.new_line)
            item.lines.append(self.new_line)

    def get_center(self):
        rect = self.boundingRect()
        center = None
        if self.base.socket_type == SocketType.OUT:
            center = qt.QtCore.QPointF(self.node_width + 14, rect.y() + rect.height() / 2.0)
        if self.base.socket_type == SocketType.IN:
            center = qt.QtCore.QPointF(rect.x() + rect.width() / 2.0, rect.y() + rect.height() / 2.0)
        if self.base.socket_type == SocketType.TOP:
            center = qt.QtCore.QPointF(rect.x() + rect.width() / 2.0, rect.y() + rect.height() / 2.0)

        center = self.mapToScene(center)

        return center

    def get_parent(self):
        return self.base.parent


class NodeSocket(AttributeItem):
    item_type = ItemType.SOCKET

    def __init__(self, socket_type=SocketType.IN, name=None, value=None, data_type=None):
        self.socket_type = socket_type
        self.dirty = True
        self.parent = None
        self.lines = []

        super(NodeSocket, self).__init__()

        self._name = name
        self._value = value
        self._data_type = data_type

        self.graphic = None
        if not qt.is_batch():
            self.graphic = NodeSocketItem(self)

    def remove_line(self, line_item):

        removed = False

        if line_item in self.lines:

            if line_item.source:
                line_item.source.lines.remove(line_item)
            if line_item.target:
                line_item.target.lines.remove(line_item)

            if line_item in self.lines:
                self.lines.remove(line_item)

            removed = True

        if removed:
            self.graphic.scene().removeItem(line_item.graphic)


class GraphicLine(qt.QGraphicsPathItem):

    def __init__(self, base, point_a=None, point_b=None):
        self.base = base
        super(GraphicLine, self).__init__()

        self.color = None
        self._point_a = point_a
        self._point_b = point_b
        self.setZValue(0)

        self.brush = qt.QBrush()
        self.brush.setStyle(qt.QtCore.Qt.SolidPattern)
        self.brush.setColor(qt.QColor(200, 200, 200, 255))

        self.pen = qt.QPen()
        self.pen.setStyle(qt.QtCore.Qt.SolidLine)
        self.pen.setWidth(2)
        self.pen.setColor(qt.QColor(200, 200, 200, 255))
        self.setPen(self.pen)

    def mousePressEvent(self, event):
        self.point_b = event.pos()

    def mouseMoveEvent(self, event):
        self.point_b = event.pos()

    def mouseReleaseEvent(self, event):

        items = self.scene().items(event.scenePos().toPoint())
        for item in items:
            if hasattr(item, 'item_type'):
                if item.item_type == ItemType.SOCKET:
                    if item.socket_type == SocketType.IN:
                        self.point_b = item.get_center()
                        return

        if hasattr(self.base._target.graphic, 'scene'):
            self.base._target.graphic.scene().node_disconnect.emit(self.base.source, self.base.target)

        self.base._source.remove_line(self)

    def update_path(self):
        path = qt.QPainterPath()
        path.moveTo(self.point_a)
        dx = self.point_b.x() - self.point_a.x()
        dy = self.point_b.y() - self.point_a.y()
        ctrl1 = qt.QtCore.QPointF(self.point_a.x() + dx * 0.5, self.point_a.y() + dy * 0.1)
        ctrl2 = qt.QtCore.QPointF(self.point_a.x() + dx * 0.5, self.point_a.y() + dy * 0.9)

        path.cubicTo(ctrl1, ctrl2, self.point_b)

        self.setPath(path)

    def paint(self, painter, option, widget):

        if hasattr(self, 'color') and self.color:
            color = self.color.darker(70)
            self.brush.setColor(color)
            self.pen.setColor(color)

        path = self.path()
        painter.setPen(self.pen)
        painter.drawPath(path)

        painter.setBrush(self.brush)

        painter.drawEllipse(self.point_b.x() - 3.0,
                            self.point_b.y() - 3.0,
                            6.0,
                            6.0)

        # draw arrow

        if path.length() < 50:
            return

        point = path.pointAtPercent(0.5)
        point_test = path.pointAtPercent(0.51)

        point_orig = qt.QtCore.QPointF(point.x() + 1.0, point.y())

        point_orig = point_orig - point
        point_test = point_test - point

        dot = point_orig.x() * point_test.x() + point_orig.y() * point_test.y()
        det = point_orig.x() * point_test.y() - point_orig.y() * point_test.x()
        angle = math.atan2(det, dot)

        poly = qt.QPolygonF()
        poly.append(qt.QtCore.QPointF(math.cos(angle) * 0 - math.sin(angle) * -5,
                                      math.sin(angle) * 0 + math.cos(angle) * -5))
        poly.append(qt.QtCore.QPointF(math.cos(angle) * 10 - math.sin(angle) * 0,
                                      math.sin(angle) * 10 + math.cos(angle) * 0))

        poly.append(qt.QtCore.QPointF(math.cos(angle) * 0 - math.sin(angle) * 5,
                                      math.sin(angle) * 0 + math.cos(angle) * 5))

        poly.translate(point.x(), point.y())

        painter.drawPolygon(poly)

    @property
    def point_a(self):
        return self._point_a

    @point_a.setter
    def point_a(self, point):
        self._point_a = point
        self.update_path()

    @property
    def point_b(self):
        return self._point_b

    @point_b.setter
    def point_b(self, point):
        self._point_b = point
        self.update_path()


class NodeLine(object):
    item_type = ItemType.LINE

    def __init__(self, point_a=None, point_b=None):
        self.graphic = None
        self._source = None
        self._target = None

        if not qt.is_batch():
            self.graphic = GraphicLine(self, point_a, point_b)

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, widget):
        self._source = widget

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, widget):
        self._target = widget

    def store(self):
        item_dict = {}

        source = self._source
        target = self._target

        item_dict['type'] = self.item_type

        if source:
            item_dict['source'] = source.get_parent().uuid
            item_dict['source name'] = source.name
        if target:
            item_dict['target'] = target.get_parent().uuid
            item_dict['target name'] = target.name

        return item_dict

    def load(self, item_dict):
        if 'source' not in item_dict:
            return

        source_uuid = item_dict['source']
        target_uuid = item_dict['target']

        source_name = item_dict['source name']
        target_name = item_dict['target name']

        if source_uuid in uuids and target_uuid in uuids:

            source_item = uuids[source_uuid]
            target_item = uuids[target_uuid]

            source_socket = source_item.get_socket(source_name)
            target_socket = target_item.get_socket(target_name)

            if not target_socket:
                return

            self._source = source_socket
            self._target = target_socket

            source_socket.lines.append(self)
            target_socket.lines.append(self)

            if self.graphic:

                center_a = source_socket.graphic.get_center()
                center_b = target_socket.graphic.get_center()

                self.graphic._point_a = center_a
                self.graphic._point_b = center_b

                self.graphic.color = source_socket.graphic.color

                self.graphic.update_path()

#--- Nodes


class GraphicsItem(qt.QGraphicsItem):

    def __init__(self, parent=None, base=None):
        self.base = base
        self.node_width = self._init_node_width()
        self._left_over_space = None
        self._current_socket_pos = None
        self.brush = None
        self.selPen = None
        self.pen = None
        self.rect = None

        super(GraphicsItem, self).__init__(parent)

        self._z_value = 2000

        self.draw_node()

        self.setFlag(self.ItemIsFocusable)

    def _init_node_width(self):
        return 150

    def mouseMoveEvent(self, event):
        super(GraphicsItem, self).mouseMoveEvent(event)

        selection = self.scene().selectedItems()
        if len(selection) > 1:
            return

        for name in self.base._out_sockets:
            socket = self.base._out_sockets[name]
            for line in socket.lines:
                line.graphic.point_a = line.source.graphic.get_center()
                line.graphic.point_b = line.target.graphic.get_center()

        for name in self.base._in_sockets:
            socket = self.base._in_sockets[name]
            for line in socket.lines:
                line.graphic.point_a = line.source.graphic.get_center()
                line.graphic.point_b = line.target.graphic.get_center()

    def draw_node(self):

        self._left_over_space = 0
        self._current_socket_pos = 0

        self.rect = qt.QtCore.QRect(0, 0, self.node_width, 40)
        self.setFlag(qt.QGraphicsItem.ItemIsMovable)
        self.setFlag(qt.QGraphicsItem.ItemIsSelectable)

        # Brush.
        self.brush = qt.QBrush()
        self.brush.setStyle(qt.QtCore.Qt.SolidPattern)

        self.brush.setColor(qt.QColor(*self.base._init_color()))

        # Pen.
        self.pen = qt.QPen()
        self.pen.setStyle(qt.QtCore.Qt.SolidLine)
        self.pen.setWidth(2)
        self.pen.setColor(qt.QColor(120, 120, 120, 255))

        self.selPen = qt.QPen()
        self.selPen.setStyle(qt.QtCore.Qt.SolidLine)
        self.selPen.setWidth(3)
        self.selPen.setColor(qt.QColor(255, 255, 255, 255))

    def boundingRect(self):
        return qt.QtCore.QRectF(self.rect)

    def paint(self, painter, option, widget):

        painter.setBrush(self.brush)

        if self.isSelected():
            painter.setPen(self.selPen)
        else:
            painter.setPen(self.pen)

        painter.drawRoundedRect(self.rect, 5, 5)

        pen = qt.QPen()
        pen.setStyle(qt.QtCore.Qt.SolidLine)
        pen.setWidth(1)
        pen.setColor(qt.QColor(255, 255, 255, 255))

        painter.setPen(pen)
        painter.drawText(35, -5, self.base.name)

        # self.setZValue(1000)
        # painter.drawRect(self.rect)

    def contextMenuEvent(self, event):
        self._build_context_menu(event)
        event.setAccepted(True)

    def _build_context_menu(self, event):

        menu = qt.QMenu()

        add_in_socket = menu.addAction('add in socket')
        add_out_socket = menu.addAction('add out socket')
        add_top_socket = menu.addAction('add top socket')
        add_string = menu.addAction('add string')
        add_combo = menu.addAction('add combo')
        add_color = menu.addAction('add color')

        selected_action = menu.exec_(event.screenPos())

        if selected_action == add_string:
            self.add_string()

        if selected_action == add_combo:
            self.add_combo_box()

        if selected_action == add_color:
            self.add_color_picker()

        if selected_action == add_top_socket:
            self.add_top_socket('parent', '', None)

        if selected_action == add_in_socket:
            self.add_in_socket('goo', '', None)

        if selected_action == add_out_socket:
            self.add_out_socket('foo', '', None)

    def add_space(self, item, offset=0):

        y_value = 0
        offset_y_value = 0

        if self._left_over_space:
            y_value += self._left_over_space

            self._left_over_space = 0

        # if item.item_type == ItemType.PROXY:
        #    offset_y_value += 4

        y_value = self._current_socket_pos + offset + offset_y_value

        self.rect = qt.QtCore.QRect(0, 0, self.node_width, y_value + 35)
        item.setY(y_value)

        y_value += 18

        self._current_socket_pos = y_value
        self._left_over_space = offset

        item.setZValue(self._z_value)
        self._z_value -= 1


class NodeItem(object):
    item_type = ItemType.NODE
    item_name = 'Node'

    def __init__(self, name='', uuid_value=None):
        self.uuid = None
        self._current_socket_pos = None
        self._dirty = None
        self.orig_position = [0, 0]

        self._color = self._init_color()

        self.graphic = None
        if not qt.is_batch():
            self.graphic = GraphicsItem(base=self)
            self.graphic.node_width = self._init_node_width()

        super(NodeItem, self).__init__()

        self.rig = self._init_rig_class_instance()
        self._init_uuid(uuid_value)
        self._dirty = True
        self._signal_eval_targets = False

        if name:
            self.name = name
        else:
            self.name = self.item_name

        self._widgets = []
        self._in_sockets = {}
        self._in_socket_widgets = {}
        self._out_sockets = {}
        self._sockets = {}
        self._dependency = {}

        # if self.graphic:
        self._build_items()

    def __getattribute__(self, item):
        dirty = object.__getattribute__(self, '_dirty')

        if item == 'run' and not dirty:
            return lambda *args: None

        return object.__getattribute__(self, item)

    def _init_uuid(self, uuid_value):
        if uuid_value:
            self.uuid = uuid_value
        else:
            self.uuid = str(uuid.uuid4())

        uuids[self.uuid] = self

    def _init_rig_class_instance(self):
        return rigs.Base()

    def _init_color(self):
        return [68, 68, 68, 255]

    def _init_node_width(self):
        return 150

    def _dirty_run(self, attr_name=None, value=None):
        self.rig.load()

        self.dirty = True
        if hasattr(self, 'rig'):
            self.rig.dirty = True
        for out_name in self._out_sockets:
            out_sockets = self.get_outputs(out_name)
            for out_socket in out_sockets:
                out_node = out_socket.get_parent()
                out_node.dirty = True
                out_node.rig.dirty = True

        self._signal_eval_targets = True
        self.run(attr_name)
        self._signal_eval_targets = False

    def _in_widget_run(self, attr_name, attr_value=None, widget=None):
        if not widget:
            widget = self.get_widget(attr_name)

        if attr_value:
            self._set_widget_socket(attr_name, attr_value, widget)
        else:
            self._set_widget_socket(attr_name, widget.value, widget)

        self._dirty_run(attr_name)

    def _set_widget_socket(self, name, value, widget):
        util.show('\tSet widget socket %s %s' % (name, value))
        socket = self.get_socket(name)

        if not socket:
            return
        socket.value = value
        widget.value = value

    def _disconnect_lines(self):
        other_sockets = {}

        for name in self._in_sockets:
            socket = self._in_sockets[name]
            if not hasattr(socket, 'lines'):
                continue
            for line in socket.lines:
                line.target = None

                if line.source not in other_sockets:
                    other_sockets[line.source] = []

                other_sockets[line.source].append(line)

                self.graphic.scene().removeItem(line.graphic)

            socket.lines = []

        for name in self._out_sockets:
            socket = self._out_sockets[name]
            if not hasattr(socket, 'lines'):
                continue

            for line in socket.lines:
                line.source = None

                if line.target not in other_sockets:
                    other_sockets[line.target] = []

                other_sockets[line.target].append(line)

                self.graphic.scene().removeItem(line.graphic)

            socket.lines = []

        for socket in other_sockets:
            lines = other_sockets[socket]

            for line in lines:
                if line in socket.lines:
                    socket.lines.remove(line)

    def _build_items(self):
        return

    def _add_space(self, item, offset=0):
        if not self.graphic:
            return

        if hasattr(item, 'graphic'):
            item = item.graphic

        self.graphic.add_space(item, offset)

    def run_inputs(self):

        util.show('Prep: %s' % self.__class__.__name__, self.uuid)

        sockets = {}
        sockets.update(self._in_sockets)
        sockets.update(self._sockets)

        if sockets:

            for socket_name in sockets:

                input_sockets = self.get_inputs(socket_name)

                for input_socket in input_sockets:
                    if not input_socket:
                        continue
                    input_node = input_socket.get_parent()

                    if input_node.dirty:
                        input_node.run()
                    value = input_socket.value

                    current_socket = self.get_socket(socket_name)

                    current_socket.value = value

                    if hasattr(self, 'rig'):
                        self.rig.load()
                        self.rig.attr.set(socket_name, value)

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, bool_value):

        util.show('\tDIRTY: %s %s' % (bool_value, self.uuid))
        # util.show('\tRIG DIRTY: %s %s' % (self.rig.dirty, self.uuid))
        self._dirty = bool_value

    def add_top_socket(self, name, value, data_type):

        socket = NodeSocket('top', name, value, data_type)
        socket.set_parent(self)

        if not self.rig.attr.exists(name):
            self.rig.attr.add_in(name, value, data_type)

        self._in_sockets[name] = socket

        return socket

    def add_in_socket(self, name, value, data_type):
        socket = NodeSocket('in', name, value, data_type)
        socket.set_parent(self)

        if self.graphic:
            self._add_space(socket)
            current_space = self.graphic._current_socket_pos

        widget = None

        if data_type == rigs.AttrType.STRING:
            if self.graphic:
                self.graphic._current_socket_pos -= 18
            widget = self.add_string(name)

        if data_type == rigs.AttrType.COLOR:
            if self.graphic:
                self.graphic._current_socket_pos -= 30
            widget = self.add_color_picker(name)

        if data_type == rigs.AttrType.VECTOR:
            if self.graphic:
                self.graphic._current_socket_pos -= 17
            widget = self.add_vector(name)

        if widget:
            widget.value = value
            self._in_socket_widgets[name] = widget

            if self.graphic:
                widget.graphic.changed.connect(self._in_widget_run)

        if self.graphic:
            self.graphic._current_socket_pos = current_space

        if not self.rig.attr.exists(name):
            self.rig.attr.add_in(name, value, data_type)

        self._in_sockets[name] = socket

        return socket

    def add_out_socket(self, name, value, data_type):

        socket = NodeSocket('out', name, value, data_type)
        socket.set_parent(self)

        if self.graphic:
            self._add_space(socket)

        if not self.rig.attr.exists(name):
            self.rig.attr.add_out(name, value, data_type)

        self._out_sockets[name] = socket

        return socket

    def add_item(self, name, item_inst=None, track=True):

        attribute = AttributeItem(item_inst)
        attribute.name = name
        attribute.set_parent(self)

        if track:
            self._widgets.append(attribute)
            self._sockets[name] = attribute
        return attribute

    def add_bool(self, name):
        widget = None
        if self.graphic:
            widget = BoolGraphicItem(self.graphic)

        attribute_item = self.add_item(name, widget)

        self._add_space(widget, 2)

        return attribute_item

    def add_int(self, name):
        widget = None
        if self.graphic:
            widget = IntGraphicItem(self.graphic, 50)

        attribute_item = self.add_item(name, widget)

        self._add_space(widget, 4)

        return attribute_item

    def add_number(self, name):
        widget = None
        if self.graphic:
            widget = NumberGraphicItem(self.graphic)

        attribute_item = self.add_item(name, widget)

        self._add_space(widget)

        return attribute_item

    def add_vector(self, name):
        widget = None
        if self.graphic:
            widget = VectorGraphicItem(self.graphic, 105)

        attribute_item = self.add_item(name, widget)

        self._add_space(widget)

        return attribute_item

    def add_string(self, name):
        widget = None

        if self.graphic:
            rect = self.graphic.boundingRect()
            width = rect.width()
            widget = StringItem(self.graphic, width - 20)

        attribute_item = self.add_item(name, widget)

        self._add_space(widget)

        return attribute_item

    def add_color_picker(self, name, width=40, height=14):
        widget = None
        if self.graphic:
            widget = ColorPickerItem(self.graphic, width, height)

        attribute_item = self.add_item(name, widget)

        self._add_space(widget)

        return attribute_item

    def add_title(self, name):
        widget = None
        if self.graphic:
            widget = TitleItem(self.graphic)

        attribute_item = self.add_item(name, widget, track=False)
        self._add_space(widget, 3)

        return attribute_item

    def delete(self):

        self._disconnect_lines()

        if self.graphic:
            if not self.graphic.scene():
                return
            self.graphic.scene().removeItem(self.graphic)

    def get_widget(self, name):

        for widget in self._widgets:
            if widget.name == name:
                return widget

    def set_socket(self, name, value, run=False):
        util.show('\tSet socket %s %s, run: %s' % (name, value, run))
        socket = self.get_socket(name)

        if not socket:
            return

        socket.value = value

        widget = self.get_widget(name)
        if widget:
            widget.value = value

        if run:
            self.dirty = True
            self.rig.dirty = True
            self.run()

        """
        dependency_sockets = None

        if name in self._dependency:
            dependency_sockets = self._dependency[name]

        if not dependency_sockets:
            return

        for socket_name in dependency_sockets:
            dep_socket = self.get_socket(socket_name)
            value = self.rig.get_attr(socket_name)
            dep_socket.value = value
        """

        """
        for name in self._out_sockets:
            out_socket = self._out_sockets[name]

            outputs = self.get_outputs(out_socket.name)
            for output in outputs:
                node = output.parentItem()
                node.run(output.name)
        """

    def get_socket(self, name):
        sockets = self.get_all_sockets()
        if name in sockets:
            socket = sockets[name]
            return socket

    def get_all_sockets(self):
        sockets = {}
        sockets.update(self._sockets)
        sockets.update(self._in_sockets)
        sockets.update(self._out_sockets)

        return sockets

    def get_socket_value(self, name):
        socket = self.get_socket(name)
        return socket.value

    def get_inputs(self, name):
        found = []

        for socket in self._in_sockets:

            socket_inst = self._in_sockets[socket]

            if socket == name:
                for line in socket_inst.lines:
                    found.append(line.source)

        return found

    def get_outputs(self, name):

        found = []

        for out_name in self._out_sockets:
            socket = self._out_sockets[out_name]

            if socket.name == name:

                for line in socket.lines:
                    found.append(line.target)

        return found

    def get_output_connected_nodes(self):
        found = []
        for name in self._out_sockets:
            socket = self._out_sockets[name]
            for line in socket.lines:
                found.append(line.target.get_parent())

        return found

    def run(self, socket=None):
        if socket:
            util.show('Running: %s.%s' % (self.__class__.__name__, socket), self.uuid)
        else:
            util.show('Running: %s' % self.__class__.__name__, self.uuid)

        self.run_inputs()

        self.dirty = False

    def store(self):

        if self.graphic:
            position = [self.graphic.pos().x(), self.graphic.pos().y()]
        else:
            position = self.orig_position

        item_dict = {'name': self.item_name,
                     'uuid': self.uuid,
                     'type': self.item_type,
                     'position': position,
                     'widget_value': {}}

        for widget in self._widgets:
            name = widget.name
            value = widget.value
            data_type = widget.data_type

            item_dict['widget_value'][name] = {'value': value,
                                               'data_type': data_type}

        return item_dict

    def load(self, item_dict):

        self.name = item_dict['name']
        self.uuid = item_dict['uuid']
        self.rig.uuid = self.uuid

        util.show('Load Node: %s    %s' % (self.name, self.uuid))
        position = item_dict['position']
        self.orig_position = position

        if self.graphic:
            self.graphic.setPos(qt.QtCore.QPointF(position[0], position[1]))

        for widget_name in item_dict['widget_value']:
            value = item_dict['widget_value'][widget_name]['value']
            widget = self.get_widget(widget_name)
            self._set_widget_socket(widget_name, value, widget)


class ColorItem(NodeItem):
    item_type = ItemType.COLOR
    item_name = 'Color'

    def _build_items(self):

        picker = self.add_color_picker('color value', 50, 30)
        picker.data_type = rigs.AttrType.COLOR
        self.picker = picker

        picker.graphic.changed.connect(self._color_changed)

        self.add_out_socket('color', None, rigs.AttrType.COLOR)

    def _color_changed(self, name, color):

        self.color = color

        self._dirty_run()

    def run(self, socket=None):
        super(ColorItem, self).run(socket)

        socket = self.get_socket('color')
        if hasattr(self, 'color') and self.color:

            socket.value = self.color
        else:
            socket.value = self.picker.value

        update_socket_value(socket, eval_targets=self._signal_eval_targets)


class CurveShapeItem(NodeItem):
    item_type = ItemType.CURVE_SHAPE
    item_name = 'Curve Shape'

    def _init_node_width(self):
        return 180

    def _build_items(self):
        self._current_socket_pos = 10
        shapes = rigs_maya.Control.get_shapes()

        shapes.insert(0, 'Default')
        self.add_title('Maya')

        maya_widget = self.add_string('Maya')
        maya_widget.data_type = rigs.AttrType.STRING
        maya_widget.graphic.set_completion_examples(shapes[:-1])
        maya_widget.graphic.set_placeholder('Maya Curve Name')

        self._maya_curve_entry_widget = maya_widget

        maya_widget.graphic.changed.connect(self._dirty_run)

        unreal_items = unreal_lib.util.get_unreal_control_shapes()

        self.add_title('Unreal')
        unreal_widget = self.add_string('Unreal')
        unreal_widget.data_type = rigs.AttrType.STRING
        unreal_widget.graphic.set_completion_examples(unreal_items)

        self._unreal_curve_entry_widget = unreal_widget
        unreal_widget.graphic.changed.connect(self._dirty_run)

        self.add_out_socket('curve_shape', [], rigs.AttrType.STRING)

    def run(self, socket=None):
        super(CurveShapeItem, self).run(socket)

        curve = None

        if in_maya:
            curve = self._maya_curve_entry_widget.value
        if in_unreal:
            curve = self._unreal_curve_entry_widget.value

        if curve:
            socket = self.get_socket('curve_shape')
            socket.value = curve

            update_socket_value(socket, eval_targets=self._signal_eval_targets)


class TransformVectorItem(NodeItem):
    item_type = ItemType.TRANSFORM_VECTOR
    item_name = 'Transform Vector'

    def _init_node_width(self):
        return 180

    def _build_items(self):
        self._current_socket_pos = 10

        self.add_title('Maya')

        t_v = self.add_in_socket('Maya Translate', [[0.0, 0.0, 0.0]], rigs.AttrType.VECTOR)
        r_v = self.add_in_socket('Maya Rotate', [[0.0, 0.0, 0.0]], rigs.AttrType.VECTOR)
        s_v = self.add_in_socket('Maya Scale', [[1.0, 1.0, 1.0]], rigs.AttrType.VECTOR)

        self.add_title('Unreal')
        u_t_v = self.add_in_socket('Unreal Translate', [[0.0, 0.0, 0.0]], rigs.AttrType.VECTOR)
        u_r_v = self.add_in_socket('Unreal Rotate', [[0.0, 0.0, 0.0]], rigs.AttrType.VECTOR)
        u_s_v = self.add_in_socket('Unreal Scale', [[1.0, 1.0, 1.0]], rigs.AttrType.VECTOR)

        self.add_title('Output')

        self.add_out_socket('Translate', [], rigs.AttrType.VECTOR)
        self.add_out_socket('Rotate', [], rigs.AttrType.VECTOR)
        self.add_out_socket('Scale', [], rigs.AttrType.VECTOR)

    def run(self, socket=None):
        super(TransformVectorItem, self).run(socket)

        out_translate = self.get_socket('Translate')
        out_rotate = self.get_socket('Rotate')
        out_scale = self.get_socket('Scale')

        if util.is_in_unreal():
            out_translate.value = self.get_socket('Unreal Translate').value
            out_rotate.value = self.get_socket('Unreal Rotate').value
            out_scale.value = self.get_socket('Unreal Scale').value
        else:
            out_translate.value = self.get_socket('Maya Translate').value
            out_rotate.value = self.get_socket('Maya Rotate').value
            out_scale.value = self.get_socket('Maya Scale').value

        update_socket_value(out_translate, eval_targets=self._signal_eval_targets)
        update_socket_value(out_rotate, eval_targets=self._signal_eval_targets)
        update_socket_value(out_scale, eval_targets=self._signal_eval_targets)


class JointsItem(NodeItem):
    item_type = ItemType.JOINTS
    item_name = 'Joints'

    def _build_items(self):

        # self.add_in_socket('Scope', [], rigs.AttrType.TRANSFORM)
        self._current_socket_pos = 10
        line_edit = self.add_string('joint filter')
        if self.graphic:
            line_edit.graphic.set_placeholder('Joint Search')
            line_edit.graphic.changed.connect(self._dirty_run)
        line_edit.data_type = rigs.AttrType.STRING
        self.add_out_socket('joints', [], rigs.AttrType.TRANSFORM)
        # self.add_socket(socket_type, data_type, name)

        self._joint_entry_widget = line_edit

    def _get_joints(self):
        filter_text = self.get_socket_value('joint filter')
        joints = util_ramen.get_joints(filter_text[0])

        return joints

    def run(self, socket=None):
        super(JointsItem, self).run(socket)

        joints = self._get_joints()
        if joints is None:
            joints = []

        util.show('\tFound: %s' % joints)

        socket = self.get_socket('joints')
        socket.value = joints

        update_socket_value(socket, eval_targets=self._signal_eval_targets)


class ImportDataItem(NodeItem):
    item_type = ItemType.DATA
    item_name = 'Import Data'

    def _build_items(self):

        line_edit = self.add_string('data name')
        line_edit.graphic.set_placeholder('Data Name')
        line_edit.data_type = rigs.AttrType.STRING
        self.add_in_socket('Eval IN', [], rigs.AttrType.EVALUATION)
        self.add_bool('Clear Current Data')

        self.add_out_socket('result', [], rigs.AttrType.STRING)
        self.add_out_socket('Eval OUT', [], rigs.AttrType.EVALUATION)

        self._data_entry_widget = line_edit
        line_edit.graphic.changed.connect(self._dirty_run)

    def run(self, socket=None):
        super(ImportDataItem, self).run(socket)

        new_scene_widget = self._sockets['Clear Current Data']
        if new_scene_widget.value:
            if in_maya:
                cmds.file(new=True, f=True)
            if in_unreal:
                unreal_lib.util.reset_current_control_rig()

        process_inst = process.get_current_process_instance()
        result = process_inst.import_data(
            self._data_entry_widget.value[0], sub_folder=None)

        if result is None:
            result = []

        socket = self.get_socket('result')
        socket.value = result

        update_socket_value(socket, eval_targets=self._signal_eval_targets)

        return result


class PrintItem(NodeItem):
    item_type = ItemType.PRINT
    item_name = 'Print'

    def _build_items(self):
        self.add_in_socket('input', [], rigs.AttrType.ANY)

    def run(self, socket=None):
        super(PrintItem, self).run(socket)

        socket = self.get_socket('input')
        util.show(socket.value)


class SetSkeletalMeshItem(NodeItem):
    item_type = ItemType.UNREAL_SKELETAL_MESH
    item_name = 'Set Skeletal Mesh'

    def _build_items(self):
        self.add_in_socket('input', [], rigs.AttrType.STRING)

    def run(self, socket=None):
        super(SetSkeletalMeshItem, self).run(socket)

        socket = self.get_socket('input')

        util.show('\t%s' % socket.value)

        for path in socket.value:
            if unreal_lib.util.is_skeletal_mesh(path):
                unreal_lib.util.set_skeletal_mesh(path)
                util.show('Current graph: %s' % unreal_lib.util.current_control_rig)
                break


class GetSubControls(NodeItem):
    item_type = ItemType.GET_SUB_CONTROLS
    item_name = 'Get Sub Controls'

    def _build_items(self):
        self.add_in_socket('controls', [], rigs.AttrType.TRANSFORM)
        attr_name = 'control_index'

        widget = self.add_int(attr_name)
        widget.value = [-1]

        widget.graphic.changed.connect(self._dirty_run)

        self.add_out_socket('sub_controls', [], rigs.AttrType.TRANSFORM)

    def run(self, socket=None):
        super(GetSubControls, self).run(socket)
        controls = self.get_socket('controls').value

        control_index = self.get_socket_value('control_index')[0]

        sub_controls = util_ramen.get_sub_controls(controls[control_index])
        socket = self.get_socket('sub_controls')
        socket.value = sub_controls

        update_socket_value(socket, eval_targets=self._signal_eval_targets)


class RigItem(NodeItem):
    item_type = ItemType.RIG

    def __init__(self, name='', uuid_value=None):

        self._temp_parents = {}
        super(RigItem, self).__init__(name, uuid_value)

        self.rig_state = None
        # self.rig.load()

        # self.run()

    def _init_node_width(self):
        return 180

    def _init_uuid(self, uuid_value):
        super(RigItem, self)._init_uuid(uuid_value)
        self.rig.uuid = self.uuid

    def _init_rig_class_instance(self):
        return rigs.Rig()

    def _build_items(self):

        self._current_socket_pos = 10

        if not self.rig:
            return

        attribute_names = self.rig.get_all_attributes()
        ins = self.rig.get_ins()
        outs = self.rig.get_outs()
        items = self.rig.get_node_attributes()

        self._dependency.update(self.rig.get_attr_dependency())

        for attr_name in attribute_names:

            if attr_name in items:

                value, attr_type = self.rig.get_node_attribute(attr_name)
                widget = None

                if attr_type == rigs.AttrType.TITLE:
                    title = self.add_title(attr_name)
                    title.data_type = attr_type

                if attr_type == rigs.AttrType.STRING:
                    widget = self.add_string(attr_name)
                    widget.data_type = attr_type
                    widget.value = value

                if attr_type == rigs.AttrType.BOOL:
                    widget = self.add_bool(attr_name)
                    widget.data_type = attr_type
                    widget.value = value

                if attr_type == rigs.AttrType.INT:
                    widget = self.add_int(attr_name)
                    widget.data_type = attr_type
                    widget.value = value
                    widget = widget

                if attr_type == rigs.AttrType.VECTOR:
                    widget = self.add_vector(attr_name)
                    widget.data_type = attr_type
                    widget.value = value

                if widget:
                    if widget.graphic:
                        widget.graphic.changed.connect(self._dirty_run)

            if attr_name in ins:
                value, attr_type = self.rig.get_in(attr_name)

                if attr_name == 'parent':
                    self.add_top_socket(attr_name, value, attr_type)
                else:
                    self.add_in_socket(attr_name, value, attr_type)

        for attr_name in attribute_names:
            if attr_name in outs:
                value, attr_type = self.rig.get_out(attr_name)

                self.add_out_socket(attr_name, value, attr_type)

    def _run(self, socket):
        sockets = self.get_all_sockets()

        if in_unreal:
            self.rig.rig_util.load()
            if self.rig.dirty == True:
                self.rig.rig_util.build()

        for name in sockets:
            node_socket = sockets[name]

            value = node_socket.value

            if name in self._out_sockets:
                if hasattr(self, 'rig_type'):
                    value = self.rig.attr.get(name)
                    node_socket.value = value

            self.rig.attr.set(node_socket.name, value)

        if isinstance(socket, str):
            socket = sockets[socket]

        if socket:
            self.dirty = True
            self.rig.dirty = True
            update_socket_value(socket, update_rig=True)
        else:

            self.rig.create()

            if in_unreal:
                return
            for name in self._out_sockets:
                out_socket = self._out_sockets[name]
                value = self.rig.attr.get(name)
                out_socket.value = value
                update_socket_value(out_socket)

    def _unparent(self):
        if in_unreal:
            return

        nodes = self.get_output_connected_nodes()
        for node in nodes:
            self._temp_parents[node.uuid] = node
            node.rig.parent = []

    def _reparent(self):
        if in_unreal:

            inputs = self.get_inputs('parent')

            for in_socket in inputs:
                if in_socket.name == 'controls':

                    in_node = in_socket.get_parent()

                    in_node.rig.rig_util.load()
                    self.rig.rig_util.load()

                    if in_node.rig.rig_util.construct_controller:
                        in_node_unreal = in_node.rig.rig_util.construct_node
                        node_unreal = self.rig.rig_util.construct_node

                        forward_in = in_node.rig.rig_util.forward_node
                        backward_in = in_node.rig.rig_util.backward_node

                        forward_node = self.rig.rig_util.forward_node
                        backward_node = self.rig.rig_util.backward_node

                        if in_node_unreal and node_unreal:
                            in_node.rig.rig_util.construct_controller.add_link(
                                '%s.controls' % in_node_unreal.get_node_path(),
                                '%s.parent' % node_unreal.get_node_path())
                            in_node.rig.rig_util.construct_controller.add_link(
                                '%s.ExecuteContext' % in_node_unreal.get_node_path(),
                                '%s.ExecuteContext' % node_unreal.get_node_path())
                            try:
                                forward_node.rig.rig_util.forward_controller.add_link(
                                    '%s.ExecuteContext' % forward_in.get_node_path(),
                                    '%s.ExecuteContext' % forward_node.get_node_path())
                            except:
                                pass
                            try:
                                backward_node.rig.rig_util.backward_controller.add_link(
                                    '%s.ExecuteContext' % backward_in.get_node_path(),
                                    '%s.ExecuteContext' % backward_node.get_node_path())
                            except:
                                pass
        if not self._temp_parents:
            return

        controls = self.rig.get_attr('controls')
        if controls:
            for uuid in self._temp_parents:
                node = self._temp_parents[uuid]
                node.rig.parent = controls

    def run(self, socket=None):
        super(RigItem, self).run(socket)

        self.rig.load()

        self._unparent()
        self._run(socket)
        self._reparent()

        if in_unreal:
            offset = 0
            spacing = 1
            position = self.pos()
            self.rig.rig_util.set_node_position((position.x() - offset) * spacing, (position.y() - offset) * spacing)

    def delete(self):
        self._unparent()
        super(RigItem, self).delete()

        self.rig.delete()

    def store(self):
        item_dict = super(RigItem, self).store()

        item_dict['rig uuid'] = self.rig.uuid

        return item_dict

    def load(self, item_dict):
        super(RigItem, self).load(item_dict)

    def load_rig(self):

        self.rig.load()
        self.rig.uuid = self.uuid

        if in_maya:
            value = self.rig.attr.get('controls')
            if value:
                self.dirty = False
                self.rig.dirty = False

                self.set_socket('controls', value, run=False)


class FkItem(RigItem):
    item_type = ItemType.FKRIG
    item_name = 'FkRig'

    def _init_color(self):
        return [68, 68, 88, 255]

    def _init_rig_class_instance(self):
        return rigs_crossplatform.Fk()


class IkItem(RigItem):
    item_type = ItemType.IKRIG
    item_name = 'IkRig'

    def _init_color(self):
        return [68, 88, 68, 255]

    def _init_rig_class_instance(self):
        return rigs_crossplatform.Ik()

#--- registry


register_item = {
    # NodeItem.item_type : NodeItem,
    FkItem.item_type: FkItem,
    IkItem.item_type: IkItem,
    JointsItem.item_type: JointsItem,
    ColorItem.item_type: ColorItem,
    CurveShapeItem.item_type: CurveShapeItem,
    ImportDataItem.item_type: ImportDataItem,
    PrintItem.item_type: PrintItem,
    SetSkeletalMeshItem.item_type: SetSkeletalMeshItem,
    GetSubControls.item_type: GetSubControls,
    TransformVectorItem.item_type: TransformVectorItem
}


def update_socket_value(socket, update_rig=False, eval_targets=False):
    # TODO break apart it smaller functions
    source_node = socket.get_parent()
    uuid = source_node.uuid
    util.show('\tUpdate socket value %s.%s' % (source_node.name, socket.name))
    has_lines = False
    if hasattr(socket, 'lines'):
        if socket.lines:
            has_lines = True

    if has_lines:
        if socket.lines[0].target == socket:
            socket = socket.lines[0].source
            log.info('update source as socket %s' % socket.name)

    value = socket.value

    if update_rig:
        source_node.rig.set_attr(socket.name, value)
        if socket.name in source_node._widgets:
            widget = source_node._widgets
            widget.value = value

    socket.dirty = False

    outputs = source_node.get_outputs(socket.name)

    target_nodes = []

    for output in outputs:

        target_node = output.get_parent()
        if target_node not in target_nodes:
            target_nodes.append(target_node)

        util.show('\tUpdate target node %s.%s: %s\t%s' %
                  (target_node.name, output.name, value, target_node.uuid))
        run = False

        if in_unreal:

            if socket.name == 'controls' and output.name == 'parent':

                if target_node.rig.rig_util.construct_node is None:
                    target_node.rig.rig_util.load()
                    target_node.rig.rig_util.build()

                if source_node.rig.rig_util.construct_node is None:
                    source_node.rig.rig_util.load()
                    source_node.rig.rig_util.build()

                if source_node.rig.rig_util.construct_controller:
                    source_node.rig.rig_util.construct_controller.add_link('%s.controls' % source_node.rig.rig_util.construct_node.get_node_path(),
                                                                           '%s.parent' % target_node.rig.rig_util.construct_node.get_node_path())

        target_node.set_socket(output.name, value, run)

    if eval_targets:
        for target_node in target_nodes:

            util.show('\tRun target %s' % target_node.uuid)
            target_node.dirty = True
            # if in_unreal:
            #    target_node.rig.dirty = True

            target_node.run()


def connect_socket(source_socket, target_socket, run_target=True):

    source_node = source_socket.get_parent()
    target_node = target_socket.get_parent()

    current_inputs = target_node.get_inputs(target_socket.name)

    if current_inputs:
        disconnect_socket(target_socket, run_target=False)
        target_socket.remove_line(target_socket.lines[0])

    util.show('Connect socket %s.%s into %s.%s' % (source_node.name,
              source_socket.name, target_node.name, target_socket.name))

    if source_node.dirty:
        source_node.run()

    value = source_socket.value
    util.show('connect source value %s %s' % (source_socket.name, value))

    if in_unreal:

        if source_socket.name == 'controls' and target_socket.name == 'parent':

            if target_node.rig.rig_util.construct_node is None:
                target_node.rig.rig_util.load()
                target_node.rig.rig_util.build()
            if source_node.rig.rig_util.construct_controller:
                source_node.rig.rig_util.construct_controller.add_link('%s.controls' % source_node.rig.rig_util.construct_node.get_node_path(),
                                                                       '%s.parent' % target_node.rig.rig_util.construct_node.get_node_path())
                run_target = False

    target_node.set_socket(target_socket.name, value, run=run_target)


def disconnect_socket(target_socket, run_target=True):
    # TODO break apart into smaller functions
    node = target_socket.get_parent()
    util.show('Disconnect socket %s.%s %s' % (node.name, target_socket.name, node.uuid))

    node = target_socket.get_parent()

    current_input = node.get_inputs(target_socket.name)

    if not current_input:
        return

    source_socket = current_input[0]

    log.info('Remove socket value: %s %s' % (target_socket.name, node.name))

    if target_socket.name == 'joints' and not target_socket.value:
        out_nodes = node.get_output_connected_nodes()

        for out_node in out_nodes:
            if hasattr(out_node, 'rig'):
                out_node.rig.parent = []

    if target_socket.name == 'parent':

        if in_unreal:

            source_node = source_socket.get_parent()
            target_node = target_socket.get_parent()

            if target_node.rig.rig_util.construct_node is None:
                target_node.rig.rig_util.load()
                target_node.rig.rig_util.build()
            if source_node.rig.rig_util.construct_node is None:
                source_node.rig.rig_util.load()
            if source_node.rig.rig_util.construct_controller:

                source_node.rig.rig_util.construct_controller.break_link('%s.controls' % source_node.rig.rig_util.construct_node.get_node_path(),
                                                                         '%s.parent' % target_node.rig.rig_util.construct_node.get_node_path())
                run_target = False

    target_socket.remove_line(target_socket.lines[0])

    if target_socket.data_type == rigs.AttrType.TRANSFORM:
        node.set_socket(target_socket.name, None, run=run_target)
