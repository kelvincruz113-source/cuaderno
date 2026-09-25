import json,base64,copy,math
from pathlib import Path
from PySide6.QtCore import Qt,QRectF,QBuffer,QIODevice,QPointF,QSize,Signal,QMarginsF
from PySide6.QtGui import QColor,QPen,QBrush,QFont,QPixmap,QPainter,QPainterPath,QPolygonF,QAction,QKeySequence,QIcon,QPdfWriter,QPageSize,QPageLayout
from PySide6.QtWidgets import *
from gemini_webview2 import GeminiWebView2
# Carta real a 96 ppp: 8.5 x 11 pulgadas.
W,H=816,1056
ASSET_DIR=Path(__file__).resolve().parent/'assets'
STYLE=f"""QMainWindow,QDialog{{background:#0b1220;color:#f8fafc}}QToolBar{{background:#0f172a;border:0;padding:7px;spacing:5px}}QToolButton,QPushButton{{background:#25324a;color:white;border:1px solid #3a4a68;border-radius:8px;padding:8px}}QToolButton:hover,QPushButton:hover{{background:#315681}}QDockWidget{{color:white;font-weight:700}}QWidget#panel{{background:#152036}}QLabel{{color:#dbeafe}}QListWidget,QLineEdit,QSpinBox,QComboBox{{background:#111c31;color:white;border:1px solid #40506c;border-radius:7px;padding:6px}}QComboBox QAbstractItemView{{background:#111c31;color:#fff;selection-background-color:#315681;selection-color:#fff}}QSpinBox::up-arrow{{image:url({(ASSET_DIR/'up.png').as_posix()});width:10px;height:7px}}QSpinBox::down-arrow{{image:url({(ASSET_DIR/'down.png').as_posix()});width:10px;height:7px}}QStatusBar{{background:#0f172a;color:#cbd5e1}}"""
def flags():return QGraphicsItem.ItemIsMovable|QGraphicsItem.ItemIsSelectable|QGraphicsItem.ItemIsFocusable
class TextItem(QGraphicsTextItem):
 def __init__(self,text='Texto'):super().__init__(text);self.setTextInteractionFlags(Qt.NoTextInteraction);self.setFlags(flags());self.setCursor(Qt.SizeAllCursor)
 def mouseDoubleClickEvent(self,e):self.setTextInteractionFlags(Qt.TextEditorInteraction);self.setFocus();self.setCursor(Qt.IBeamCursor);super().mouseDoubleClickEvent(e)
 def focusOutEvent(self,e):self.setTextInteractionFlags(Qt.NoTextInteraction);self.setCursor(Qt.SizeAllCursor);super().focusOutEvent(e)
 def mouseReleaseEvent(self,e):super().mouseReleaseEvent(e);self.scene().views()[0].owner.commit()
class MoveRect(QGraphicsRectItem):
 def mouseReleaseEvent(self,e):super().mouseReleaseEvent(e);self.scene().views()[0].owner.commit()
class MoveEllipse(QGraphicsEllipseItem):
 def mouseReleaseEvent(self,e):super().mouseReleaseEvent(e);self.scene().views()[0].owner.commit()
class MovePath(QGraphicsPathItem):
 def mouseReleaseEvent(self,e):super().mouseReleaseEvent(e);self.scene().views()[0].owner.commit()
class MovePixmap(QGraphicsPixmapItem):
 def mouseReleaseEvent(self,e):super().mouseReleaseEvent(e);self.scene().views()[0].owner.commit()
class Canvas(QGraphicsView):
 def __init__(self,owner):
  super().__init__();self.owner=owner;self.sc=QGraphicsScene(0,0,W,H,self);self.setScene(self.sc);self.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform);self.setDragMode(QGraphicsView.RubberBandDrag);self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse);self.setBackgroundBrush(QColor('#334155'));self.page=QGraphicsRectItem(0,0,W,H);self.page.setBrush(QColor('white'));self.page.setPen(QPen(Qt.NoPen));self.page.setZValue(-10000);self.sc.addItem(self.page);self.sc.selectionChanged.connect(owner.selection_changed)
 def wheelEvent(self,e):
  if e.modifiers()&Qt.ControlModifier:
   f=1.12 if e.angleDelta().y()>0 else 1/1.12;self.scale(f,f);self.owner.update_zoom();e.accept()
  else:super().wheelEvent(e)
 def keyPressEvent(self,e):
  step=10 if e.modifiers()&Qt.ShiftModifier else 1
  if e.key()==Qt.Key_Delete:self.owner.delete_selected()
  elif e.key()==Qt.Key_Left:self.owner.nudge(-step,0)
  elif e.key()==Qt.Key_Right:self.owner.nudge(step,0)
  elif e.key()==Qt.Key_Up:self.owner.nudge(0,-step)
  elif e.key()==Qt.Key_Down:self.owner.nudge(0,step)
  else:super().keyPressEvent(e)
class ChoiceDialog(QDialog):
 def __init__(self,title,choices,kind,parent=None):
  super().__init__(parent);self.setWindowTitle(title);self.resize(620,440);l=QVBoxLayout(self);self.list=QListWidget();self.list.setViewMode(QListView.IconMode);self.list.setIconSize(QSize(112,76));self.list.setGridSize(QSize(142,116));self.list.setResizeMode(QListView.Adjust);self.list.setSpacing(8);self.list.setWordWrap(True)
  for name in choices:
   item=QListWidgetItem(self.preview(name,kind),name);item.setTextAlignment(Qt.AlignHCenter);self.list.addItem(item)
  self.list.setCurrentRow(0);self.list.itemDoubleClicked.connect(self.accept);l.addWidget(self.list);b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);b.accepted.connect(self.accept);b.rejected.connect(self.reject);l.addWidget(b)
 def preview(self,name,kind):
  pm=QPixmap(112,76);pm.fill(QColor('#172033'));q=QPainter(pm);q.setRenderHint(QPainter.Antialiasing);pen=QPen(QColor('#f8fafc'),4);q.setPen(pen);q.setBrush(QColor('#3b82f6'))
  if kind=='line':
   pen.setStyle(Qt.DashLine if 'discontinua' in name else Qt.DotLine if 'punteada' in name else Qt.SolidLine);pen.setWidth(8 if 'gruesa' in name or 'doble' in name else 3);q.setPen(pen);q.drawLine(12,38,98,38)
   if 'Flecha' in name:q.drawLine(84,26,100,38);q.drawLine(84,50,100,38)
  else:
   if name in ('Círculo','Elipse'):q.drawEllipse(QRectF(28,10,56 if name=='Círculo' else 70,56 if name=='Círculo' else 44))
   elif name=='Triángulo':q.drawPolygon(QPolygonF([QPointF(56,8),QPointF(94,64),QPointF(18,64)]))
   elif name=='Rombo':q.drawPolygon(QPolygonF([QPointF(56,8),QPointF(96,38),QPointF(56,68),QPointF(16,38)]))
   elif name=='Pentágono':q.drawPolygon(QPolygonF([QPointF(56,7),QPointF(96,31),QPointF(80,68),QPointF(32,68),QPointF(16,31)]))
   elif name=='Hexágono':q.drawPolygon(QPolygonF([QPointF(32,8),QPointF(80,8),QPointF(102,38),QPointF(80,68),QPointF(32,68),QPointF(10,38)]))
   elif name=='Estrella':q.drawText(QRectF(0,0,112,76),Qt.AlignCenter,'★')
   elif name=='Escudo':q.drawPolygon(QPolygonF([QPointF(20,10),QPointF(92,10),QPointF(84,52),QPointF(56,70),QPointF(28,52)]))
   elif name=='Burbuja':q.drawRoundedRect(16,12,80,44,10,10);q.drawPolygon(QPolygonF([QPointF(44,56),QPointF(36,70),QPointF(60,56)]))
   elif name=='Etiqueta':q.drawPolygon(QPolygonF([QPointF(14,16),QPointF(78,16),QPointF(100,38),QPointF(78,60),QPointF(14,60)]))
   else:q.drawRoundedRect(QRectF(24,12,64,52),10,10)
  q.end();return QIcon(pm)
 def value(self):return self.list.currentItem().text() if self.list.currentItem() else ''
class CoverAIStudio(QMainWindow):
 saved=Signal(str,str)
 def __init__(self,project_path,pdf_path,cover_data=None,parent=None):
  super().__init__(parent);self.setAttribute(Qt.WA_DeleteOnClose);self.setWindowTitle('CoverAI Studio V7 - Portada tamaño Carta');self.resize(1450,900);self.setStyleSheet(STYLE);self.project_path=Path(project_path);self.pdf_path=Path(pdf_path);self.cover_data=cover_data or {};self.history=[];self.future=[];self.loading=False;self.canvas=Canvas(self);self.setCentralWidget(self.canvas);self.toolbar();self.left();self.right()
  if self.project_path.exists():self.load_project()
  else:self.template_from_data(self.cover_data)
  self.commit();self.fit_page();self.statusBar().showMessage('Página Carta 8.5 × 11. Arrastra objetos y haz doble clic para editar texto.')
 def toolbar(self):
  b=self.addToolBar('Principal');b.setMovable(False)
  for n,k,f in [('Nuevo','Ctrl+N',self.new),('Guardar','Ctrl+S',self.save),('Deshacer','Ctrl+Z',self.undo),('Rehacer','Ctrl+Y',self.redo),('Duplicar','Ctrl+D',self.duplicate),('Eliminar','Delete',self.delete_selected)]:a=QAction(n,self);a.setShortcut(QKeySequence(k));a.triggered.connect(f);b.addAction(a)
  b.addSeparator();bm=QPushButton('−');bm.clicked.connect(self.zoom_out);b.addWidget(bm);self.zoom=QComboBox();self.zoom.addItems(['25%','50%','75%','100%','125%','150%','200%','300%']);self.zoom.setCurrentText('75%');self.zoom.currentTextChanged.connect(self.zoom_select);b.addWidget(self.zoom);bp=QPushButton('+');bp.clicked.connect(self.zoom_in);b.addWidget(bp);bf=QPushButton('Ajustar página');bf.clicked.connect(self.fit_page);b.addWidget(bf);bg=QPushButton('Generar imagen por Gemini');bg.clicked.connect(self.open_gemini);b.addWidget(bg)
 def left(self):
  d=QDockWidget('Elementos',self);d.setMinimumWidth(270);w=QWidget();w.setObjectName('panel');l=QVBoxLayout(w)
  for t,f in [('Añadir título',lambda:self.add_text('TÍTULO PRINCIPAL',42,True)),('Añadir subtítulo',lambda:self.add_text('Subtítulo',24)),('Añadir texto',lambda:self.add_text('Escribe aquí',18)),('Añadir imagen',self.add_image),('Añadir formas',self.shape_pack),('Añadir líneas',self.line_pack),('Fondo del lienzo',self.background)]:q=QPushButton(t);q.clicked.connect(f);l.addWidget(q)
  l.addWidget(QLabel('PLANTILLAS DE DERECHO'));self.templates=QComboBox();self.templates.addItems(['Selecciona una plantilla','Teoría General del Proceso','Derecho Constitucional','Derecho Penal','Derecho Civil','Derecho Procesal','Derecho Mercantil','Derecho Laboral','Derecho Administrativo','Derecho Internacional','Derechos Humanos','Filosofía del Derecho','Investigación Jurídica','Tesis Jurídica','Cuaderno Jurídico Editorial']);l.addWidget(self.templates);q=QPushButton('Aplicar plantilla');q.clicked.connect(self.apply_template);l.addWidget(q);l.addStretch();d.setWidget(w);self.addDockWidget(Qt.LeftDockWidgetArea,d)
 def right(self):
  d=QDockWidget('Propiedades y capas',self);d.setMinimumWidth(290);w=QWidget();w.setObjectName('panel');l=QVBoxLayout(w);f=QFormLayout();self.size=QSpinBox();self.size.setRange(8,120);self.size.valueChanged.connect(self.font_size);self.rot=QSpinBox();self.rot.setRange(-180,180);self.rot.valueChanged.connect(self.rotation);self.scale_box=QSpinBox();self.scale_box.setRange(10,300);self.scale_box.setValue(100);self.scale_box.valueChanged.connect(self.scaling);f.addRow('Tamaño',self.size);f.addRow('Rotación',self.rot);f.addRow('Escala %',self.scale_box);l.addLayout(f)
  for t,fn in [('Color',self.item_color),('Negrita',self.bold),('Centrar horizontal',self.center_h),('Centrar vertical',self.center_v),('Centrar totalmente',self.center_all),('Subir capa',lambda:self.layer(1)),('Bajar capa',lambda:self.layer(-1)),('Bloquear/Desbloquear',self.lock)]:q=QPushButton(t);q.clicked.connect(fn);l.addWidget(q)
  l.addWidget(QLabel('CAPAS'));self.layers=QListWidget();self.layers.itemClicked.connect(self.pick_layer);l.addWidget(self.layers);d.setWidget(w);self.addDockWidget(Qt.RightDockWidgetArea,d)
 def selected(self):a=self.canvas.sc.selectedItems();return a[0] if a else None
 def selection_changed(self):
  i=self.selected()
  if i:
   for box,val in [(self.rot,round(i.rotation())),(self.scale_box,round(i.scale()*100))]:box.blockSignals(True);box.setValue(val);box.blockSignals(False)
   if isinstance(i,QGraphicsTextItem):self.size.blockSignals(True);self.size.setValue(max(8,i.font().pointSize()));self.size.blockSignals(False)
  self.refresh()
 def common(self,i,name,x,y,z=0):i.setPos(x,y);i.setFlags(flags());i.setData(0,name);i.setZValue(z);self.canvas.sc.addItem(i);return i
 def add_text(self,t,size=24,bold=False,x=110,y=160,c='#172033',z=1,save=True):i=TextItem(t);i.setFont(QFont('Arial',size,QFont.Bold if bold else QFont.Normal));i.setDefaultTextColor(QColor(c));self.common(i,t[:28],x,y,z);self.refresh();self.commit() if save else None;return i
 def add_rect(self,x=120,y=420,w=550,h=180,c='#dbeafe',name='Rectángulo',z=0,save=True):i=MoveRect(0,0,w,h);i.setBrush(QColor(c));i.setPen(QPen(Qt.NoPen));self.common(i,name,x,y,z);self.refresh();self.commit() if save else None;return i
 def add_ellipse(self,x=300,y=430,w=190,h=150,c='#bfdbfe',name='Elipse',z=0,save=True):i=MoveEllipse(0,0,w,h);i.setBrush(QColor(c));i.setPen(QPen(Qt.NoPen));self.common(i,name,x,y,z);self.refresh();self.commit() if save else None;return i
 def add_path(self,path,x,y,c='#93c5fd',name='Forma',z=0,fill=True,save=True,penw=4,style=Qt.SolidLine):i=MovePath(path);i.setBrush(QColor(c) if fill else Qt.NoBrush);i.setPen(QPen(QColor(c),penw,style));self.common(i,name,x,y,z);self.refresh();self.commit() if save else None;return i
 def open_gemini(self):
  try:
   if getattr(self,'gemini_window',None) is None:
    self.gemini_window=GeminiWebView2(self);self.gemini_window.image_applied.connect(self.apply_gemini_image)
   self.gemini_window.show();self.gemini_window.raise_();self.gemini_window.activateWindow()
  except Exception as exc:QMessageBox.warning(self,'Gemini WebView2',f'No se pudo abrir WebView2.\n{exc}')
 def apply_gemini_image(self,path):
  pm=QPixmap(path)
  if pm.isNull():QMessageBox.warning(self,'Gemini','La imagen no pudo cargarse.');return
  pm=pm.scaled(W,H,Qt.IgnoreAspectRatio,Qt.SmoothTransformation);item=MovePixmap(pm);self.common(item,'Imagen Gemini',0,0,-9000);self.commit();self.refresh();self.statusBar().showMessage('Imagen Gemini aplicada. Pulsa Guardar para actualizar la portada.')
 def add_image(self):
  p,_=QFileDialog.getOpenFileName(self,'Añadir imagen','','Imágenes (*.png *.jpg *.jpeg *.webp)')
  if not p:return
  pm=QPixmap(p)
  if pm.isNull():return
  pm=pm.scaled(520,520,Qt.KeepAspectRatio,Qt.SmoothTransformation);self.common(MovePixmap(pm),'Imagen',(W-pm.width())/2,320,1);self.commit();self.refresh()
 def shape_pack(self):
  choices=['Rectángulo','Rectángulo fino','Círculo','Elipse','Triángulo','Rombo','Pentágono','Hexágono','Estrella','Escudo','Burbuja','Etiqueta'];d=ChoiceDialog('Pack de formas',choices,'shape',self)
  if d.exec()!=QDialog.Accepted:return
  v=d.value()
  if v=='Rectángulo':self.add_rect();return
  if v=='Rectángulo fino':self.add_rect(180,460,430,90,'#bfdbfe',v);return
  if v=='Círculo':self.add_ellipse(305,430,185,185,'#bfdbfe',v);return
  if v=='Elipse':self.add_ellipse(name=v);return
  pts={'Triángulo':[(100,160),(0,160),(50,0)],'Rombo':[(80,0),(160,80),(80,160),(0,80)],'Pentágono':[(80,0),(160,60),(130,160),(30,160),(0,60)],'Hexágono':[(45,0),(135,0),(180,80),(135,160),(45,160),(0,80)],'Escudo':[(0,0),(160,0),(145,110),(80,170),(15,110)],'Etiqueta':[(0,0),(140,0),(180,70),(140,140),(0,140)],'Burbuja':[(0,0),(190,0),(190,110),(80,110),(45,145),(50,110),(0,110)]}
  ps=[(90+(90 if n%2==0 else 40)*math.cos(-math.pi/2+n*math.pi/5),90+(90 if n%2==0 else 40)*math.sin(-math.pi/2+n*math.pi/5)) for n in range(10)] if v=='Estrella' else pts[v];path=QPainterPath();path.moveTo(*ps[0]);[path.lineTo(*p) for p in ps[1:]];path.closeSubpath();self.add_path(path,300,430,'#bfdbfe',v)
 def line_pack(self):
  choices=['Línea fina','Línea gruesa','Línea discontinua','Línea punteada','Línea doble','Flecha derecha','Flecha doble','Ángulo','Zigzag','Separador editorial'];d=ChoiceDialog('Pack de líneas',choices,'line',self)
  if d.exec()!=QDialog.Accepted:return
  v=d.value();p=QPainterPath();p.moveTo(0,0);style=Qt.SolidLine;w=4
  if v in choices[:5]+['Separador editorial']:p.lineTo(500,0)
  elif v=='Flecha derecha':p.lineTo(500,0);p.moveTo(470,-22);p.lineTo(500,0);p.lineTo(470,22)
  elif v=='Flecha doble':p.moveTo(30,-22);p.lineTo(0,0);p.lineTo(30,22);p.moveTo(0,0);p.lineTo(500,0);p.moveTo(470,-22);p.lineTo(500,0);p.lineTo(470,22)
  elif v=='Ángulo':p.lineTo(250,90);p.lineTo(500,0)
  else:
   for n in range(1,11):p.lineTo(n*50,25 if n%2 else 0)
  if v=='Línea fina':w=2
  elif v=='Línea gruesa':w=10
  elif v=='Línea discontinua':style=Qt.DashLine
  elif v=='Línea punteada':style=Qt.DotLine
  elif v=='Línea doble':w=8
  elif v=='Separador editorial':w=6
  self.add_path(p,145,430,'#2563eb',v,fill=False,penw=w,style=style)
 def apply_template(self):
  n=self.templates.currentText()
  if n=='Selecciona una plantilla':QMessageBox.information(self,'Plantillas','Selecciona una plantilla.');return
  self.template(n);self.commit()
 def template_from_data(self,d):
  self.clear();self.canvas.page.setBrush(QColor(d.get('color') or '#146C82'));fg=d.get('font_color') or '#fff';self.add_text((d.get('subtitle') or 'CUADERNO DE ESTUDIO').upper(),22,False,95,180,fg,1,False);self.add_text((d.get('title') or 'MI CUADERNO JURÍDICO').upper(),40,True,90,330,fg,1,False);self.add_text('\n'.join([d.get(k,'') for k in ('author','faculty','career','university','year') if d.get(k)]),20,False,120,600,fg,1,False);self.add_rect(24,24,W-48,H-48,'#00000000','Marco',5,False).setPen(QPen(QColor('#D9A06C'),4));self.loading=False;self.refresh()
 def template(self,n):
  self.clear();palette={'Derecho Constitucional':('#173f73','#d4af37','#ffffff'),'Derecho Penal':('#651a23','#111111','#ffffff'),'Derecho Civil':('#efe3cf','#795548','#3e2723'),'Derecho Laboral':('#285943','#d8b45a','#ffffff'),'Tesis Jurídica':('#ffffff','#7f1d1d','#111827')};a,b,t=palette.get(n,('#0e6b83','#050505','#ffffff'));self.canvas.page.setBrush(QColor(a));self.add_rect(0,0,W,230,b,'Cabecera',-5,False);self.add_text(n.upper(),40,True,70,75,'#ffffff',1,False);self.add_text('CUADERNO DE ESTUDIO',21,False,75,155,'#f8fafc',1,False);self.add_rect(90,320,636,350,'#ffffff','Área de imagen',-3,False);self.add_text('Imagen o símbolo jurídico',21,True,250,480,b,1,False);self.add_text('Nombre del estudiante',22,False,260,800,t,1,False);self.add_text('Universidad · 2026',18,True,300,900,t,1,False);self.loading=False;self.refresh()
 def background(self):
  c=QColorDialog.getColor(self.canvas.page.brush().color(),self)
  if c.isValid():self.canvas.page.setBrush(c);self.commit()
 def item_color(self):
  i=self.selected();c=QColorDialog.getColor(parent=self)
  if not i or not c.isValid():return
  if isinstance(i,QGraphicsTextItem):i.setDefaultTextColor(c)
  elif isinstance(i,QGraphicsPathItem):i.setPen(QPen(c,i.pen().width(),i.pen().style()));i.setBrush(c if i.brush().style()!=Qt.NoBrush else Qt.NoBrush)
  elif hasattr(i,'setBrush'):i.setBrush(c)
  self.commit()
 def font_size(self,v):
  i=self.selected()
  if isinstance(i,QGraphicsTextItem):f=i.font();f.setPointSize(v);i.setFont(f);self.commit()
 def bold(self):
  i=self.selected()
  if isinstance(i,QGraphicsTextItem):f=i.font();f.setBold(not f.bold());i.setFont(f);self.commit()
 def rotation(self,v):
  i=self.selected()
  if i:i.setTransformOriginPoint(i.boundingRect().center());i.setRotation(v);self.commit()
 def scaling(self,v):
  i=self.selected()
  if i:i.setTransformOriginPoint(i.boundingRect().center());i.setScale(v/100);self.commit()
 def center_h(self):
  i=self.selected()
  if i:i.setX((W-i.boundingRect().width()*i.scale())/2);self.commit()
 def center_v(self):
  i=self.selected()
  if i:i.setY((H-i.boundingRect().height()*i.scale())/2);self.commit()
 def center_all(self):self.center_h();self.center_v()
 def layer(self,d):
  i=self.selected()
  if i:i.setZValue(i.zValue()+d);self.commit();self.refresh()
 def lock(self):
  i=self.selected()
  if i:i.setFlag(QGraphicsItem.ItemIsMovable,not bool(i.flags()&QGraphicsItem.ItemIsMovable));self.commit()
 def nudge(self,x,y):
  for i in self.canvas.sc.selectedItems():i.moveBy(x,y)
  self.commit()
 def delete_selected(self):
  for i in self.canvas.sc.selectedItems():
   if i is not self.canvas.page:self.canvas.sc.removeItem(i)
  self.commit();self.refresh()
 def duplicate(self):
  i=self.selected()
  if not i:return
  d=self.item_data(i);d['x']+=25;d['y']+=25;self.make_item(d,True);self.commit()
 def clear(self):
  self.loading=True
  for i in list(self.canvas.sc.items()):
   if i is not self.canvas.page:self.canvas.sc.removeItem(i)
  self.canvas.page.setBrush(QColor('white'));self.loading=False;self.refresh()
 def new(self):self.clear();self.commit()
 def item_data(self,i):
  o={'x':i.x(),'y':i.y(),'z':i.zValue(),'rot':i.rotation(),'scale':i.scale(),'name':str(i.data(0) or 'Elemento'),'movable':bool(i.flags()&QGraphicsItem.ItemIsMovable)}
  if isinstance(i,QGraphicsTextItem):o.update(type='text',text=i.toPlainText(),size=i.font().pointSize(),bold=i.font().bold(),color=i.defaultTextColor().name())
  elif isinstance(i,QGraphicsEllipseItem):o.update(type='ellipse',w=i.rect().width(),h=i.rect().height(),color=i.brush().color().name())
  elif isinstance(i,QGraphicsRectItem):o.update(type='rect',w=i.rect().width(),h=i.rect().height(),color=i.brush().color().name(),pen=i.pen().color().name(),penw=i.pen().width())
  elif isinstance(i,QGraphicsPathItem):o.update(type='path',points=[(i.path().elementAt(x).x,i.path().elementAt(x).y,int(i.path().elementAt(x).type)) for x in range(i.path().elementCount())],color=i.pen().color().name(),penw=i.pen().width(),style=int(i.pen().style().value),fill=i.brush().style()!=Qt.NoBrush)
  elif isinstance(i,QGraphicsPixmapItem):buf=QBuffer();buf.open(QIODevice.WriteOnly);i.pixmap().save(buf,'PNG');o.update(type='image',data=base64.b64encode(bytes(buf.data())).decode())
  return o
 def state(self):return {'page_size':'LETTER','width':W,'height':H,'background':self.canvas.page.brush().color().name(),'items':[self.item_data(i) for i in reversed(self.canvas.sc.items()) if i is not self.canvas.page]}
 def make_item(self,o,select=False):
  t=o['type']
  if t=='text':i=self.add_text(o['text'],o['size'],o['bold'],o['x'],o['y'],o['color'],o['z'],False)
  elif t=='rect':i=self.add_rect(o['x'],o['y'],o['w'],o['h'],o['color'],o['name'],o['z'],False);i.setPen(QPen(QColor(o.get('pen','#00000000')),o.get('penw',0)))
  elif t=='ellipse':i=self.add_ellipse(o['x'],o['y'],o['w'],o['h'],o['color'],o['name'],o['z'],False)
  elif t=='path':
   p=QPainterPath()
   for x,y,k in o['points']:p.moveTo(x,y) if k==0 else p.lineTo(x,y)
   i=self.add_path(p,o['x'],o['y'],o['color'],o['name'],o['z'],o['fill'],False,o['penw'],Qt.PenStyle(o.get('style',1)))
  else:pm=QPixmap();pm.loadFromData(base64.b64decode(o['data']));i=self.common(MovePixmap(pm),o['name'],o['x'],o['y'],o['z'])
  i.setRotation(o.get('rot',0));i.setScale(o.get('scale',1));i.setFlag(QGraphicsItem.ItemIsMovable,o.get('movable',True));i.setSelected(select);return i
 def restore(self,st):
  self.clear();self.loading=True;self.canvas.page.setBrush(QColor(st['background']));[self.make_item(o) for o in st['items']];self.loading=False;self.refresh()
 def commit(self):
  if self.loading:return
  st=self.state()
  if not self.history or st!=self.history[-1]:self.history.append(copy.deepcopy(st));self.history=self.history[-80:];self.future.clear()
 def undo(self):
  if len(self.history)<2:return
  self.future.append(self.history.pop());self.restore(copy.deepcopy(self.history[-1]))
 def redo(self):
  if not self.future:return
  st=self.future.pop();self.history.append(copy.deepcopy(st));self.restore(st)
 def refresh(self):
  if not hasattr(self,'layers'):return
  self.layers.clear()
  for i in sorted([x for x in self.canvas.sc.items() if x is not self.canvas.page],key=lambda x:x.zValue(),reverse=True):q=QListWidgetItem(str(i.data(0) or type(i).__name__));q.setData(Qt.UserRole,id(i));self.layers.addItem(q)
 def pick_layer(self,q):
  target=q.data(Qt.UserRole)
  for i in self.canvas.sc.items():i.setSelected(id(i)==target)
 def zval(self):return round(self.canvas.transform().m11()*100)
 def update_zoom(self):v=f'{self.zval()}%';self.zoom.blockSignals(True);self.zoom.setCurrentText(v);self.zoom.blockSignals(False)
 def set_zoom(self,v):self.canvas.resetTransform();self.canvas.scale(v/100,v/100);self.update_zoom()
 def zoom_in(self):self.set_zoom(min(500,self.zval()+10))
 def zoom_out(self):self.set_zoom(max(10,self.zval()-10))
 def zoom_select(self,t):
  try:self.set_zoom(int(t.replace('%','')))
  except:pass
 def fit_page(self):self.canvas.fitInView(QRectF(0,0,W,H),Qt.KeepAspectRatio);self.update_zoom()
 def load_project(self):
  try:self.restore(json.loads(self.project_path.read_text(encoding='utf-8')))
  except Exception:self.template_from_data(self.cover_data)
 def export_pdf(self):
  self.pdf_path.parent.mkdir(parents=True,exist_ok=True);writer=QPdfWriter(str(self.pdf_path));writer.setPageSize(QPageSize(QPageSize.Letter));writer.setPageMargins(QMarginsF(0,0,0,0),QPageLayout.Point);p=QPainter(writer);self.canvas.sc.render(p,QRectF(0,0,writer.width(),writer.height()),QRectF(0,0,W,H),Qt.IgnoreAspectRatio);p.end()
 def save(self):self.project_path.parent.mkdir(parents=True,exist_ok=True);self.project_path.write_text(json.dumps(self.state(),ensure_ascii=False),encoding='utf-8');self.export_pdf();self.saved.emit(str(self.project_path),str(self.pdf_path));self.statusBar().showMessage('Guardado. PDF Carta actualizado.')
