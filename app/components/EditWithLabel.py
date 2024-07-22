from PyQt5.QtWidgets import QApplication, QLabel, QSizePolicy, QTextEdit, QWidget,QHBoxLayout,QFrame,QGraphicsDropShadowEffect,QGraphicsOpacityEffect
from PyQt5.QtCore import Qt,QPropertyAnimation,QEasingCurve,QEvent
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPalette, QPixmap,QResizeEvent
from qfluentwidgets import StyleSheetBase, Theme, isDarkTheme, qconfig,PrimaryPushButton,ComboBox,LineEdit

class LabeledLineEdit(QWidget):
    def __init__(self, label_text, parent=None):
        super().__init__(parent)

        self.initUI(label_text)

    def initUI(self, label_text):
        hbox = QHBoxLayout()
        hbox.setSpacing(0)  # 设置控件之间的间距为0
        # 创建标签
        label = QLabel(label_text, self)

        # 创建输入框
        self.line_edit = LineEdit(self)
        self.line_edit.setMaximumWidth(80)
        # 确保 QLineEdit 能够收缩
        size_policy = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.line_edit.setSizePolicy(size_policy)
        # 将标签和输入框添加到水平布局中
        hbox.addWidget(label)
        hbox.addWidget(self.line_edit, 1, Qt.AlignLeft)

        self.setLayout(hbox)

    def text(self):
        return self.line_edit.text()

    def setText(self, text):
        self.line_edit.setText(text)