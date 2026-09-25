from pathlib import Path
from PIL import Image, ImageOps
from PySide6.QtCore import Qt,QTimer,QStandardPaths,Signal,QCoreApplication
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMainWindow,QWidget,QVBoxLayout,QLabel,QPushButton,QSplitter,QSizePolicy,QMessageBox
GEMINI_URL='https://gemini.google.com/image-gen'
EXTENSIONS={'.png','.jpg','.jpeg','.webp','.avif'}
LETTER_PIXELS=(2550,3300)
class GeminiWebView2(QMainWindow):
    image_applied=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent);QCoreApplication.setOrganizationName('KelvinApps');QCoreApplication.setApplicationName('CuadernoJuridicoWebView2');self.setAttribute(Qt.WA_DeleteOnClose,False);self.setWindowTitle('Gemini integrado con Microsoft Edge WebView2');self.resize(1240,600);self.setMinimumSize(920,600)
        downloads=QStandardPaths.writableLocation(QStandardPaths.DownloadLocation);self.downloads=Path(downloads) if downloads else Path.home()/'Downloads';self.folder=self.downloads/'GeminiPortadas';self.output=self.folder/'PDF';self.folder.mkdir(parents=True,exist_ok=True);self.output.mkdir(parents=True,exist_ok=True);self.current=None;self.known=self.images();self.build_ui();self.build_webview();self.timer=QTimer(self);self.timer.timeout.connect(self.scan);self.timer.start(900);self.latest()
    def build_ui(self):
        panel=QWidget();panel.setObjectName('previewPanel');layout=QVBoxLayout(panel);layout.setContentsMargins(14,14,14,14);layout.setSpacing(9);title=QLabel('VISTA PREVIA');title.setAlignment(Qt.AlignCenter);title.setObjectName('title');self.sheet=QLabel('Genera y descarga una imagen desde Gemini.');self.sheet.setAlignment(Qt.AlignCenter);self.sheet.setObjectName('sheet');self.sheet.setMinimumSize(250,330);self.sheet.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);self.info=QLabel('Iniciando Microsoft Edge WebView2…');self.info.setAlignment(Qt.AlignCenter);self.info.setWordWrap(True);self.apply=QPushButton('Aplicar imagen al editor');self.apply.setObjectName('apply');self.apply.setEnabled(False);self.apply.clicked.connect(self.apply_image)
        layout.addWidget(title);layout.addWidget(self.sheet,1);layout.addWidget(self.info);layout.addWidget(self.apply)
        self.web_host=QWidget();self.web_layout=QVBoxLayout(self.web_host);self.web_layout.setContentsMargins(0,0,0,0);self.splitter=QSplitter(Qt.Horizontal);self.splitter.addWidget(panel);self.splitter.addWidget(self.web_host);self.splitter.setStretchFactor(0,0);self.splitter.setStretchFactor(1,1);self.splitter.setSizes([350,890]);self.setCentralWidget(self.splitter)
        self.setStyleSheet('QMainWindow,QWidget{background:#111827;color:#e5e7eb}#previewPanel{background:#0f172a}#title{font-weight:700;color:#c4b5fd;padding:7px}#sheet{background:#fff;color:#64748b;border:1px solid #475569}QPushButton{background:#334155;color:white;padding:10px;border:0;border-radius:8px;font-weight:600}#apply{background:#16a34a}#apply:disabled{background:#334155;color:#64748b}QSplitter::handle{background:#334155}')
    def build_webview(self):
        try:
            from qtwebview2 import QtWebView2Widget
            self.webview=QtWebView2Widget(parent=self.web_host,url=GEMINI_URL)
            self.web_layout.addWidget(self.webview,1);self.info.setText('Gemini abierto dentro del programa. La sesión se conserva en WebView2.')
        except Exception as exc:
            self.webview=None;msg=QLabel('No se pudo iniciar WebView2.\n\n'+str(exc));msg.setAlignment(Qt.AlignCenter);msg.setWordWrap(True);self.web_layout.addWidget(msg,1);retry=QPushButton('Reintentar WebView2');retry.clicked.connect(self.retry);self.web_layout.addWidget(retry);self.info.setText('WebView2 no está disponible. Ejecuta INSTALAR_WEBVIEW2.bat.')
    def retry(self):
        if self.webview is not None:
            try:self.webview.reload();return
            except Exception:pass
        QMessageBox.information(self,'WebView2','Cierra el programa, ejecuta INSTALAR_WEBVIEW2.bat y vuelve a abrirlo.')
    def images(self):
        out=set()
        for folder in (self.downloads,self.folder):
            if folder.exists():
                for p in folder.iterdir():
                    if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.name.endswith(('.crdownload','.tmp','.download')):out.add(p.resolve())
        return out
    def scan(self):
        now=self.images();new=now-self.known;self.known=now
        if new:self.prepare(max(new,key=lambda p:p.stat().st_mtime))
    def latest(self):
        files=self.images()
        if files:self.prepare(max(files,key=lambda p:p.stat().st_mtime))
    def prepare(self,source):
        try:
            if self.output in source.parents:return
            with Image.open(source) as im:
                im=ImageOps.exif_transpose(im).convert('RGB');fit=ImageOps.fit(im,LETTER_PIXELS,Image.Resampling.LANCZOS,centering=(.5,.5));target=self.output/f'{source.stem}_carta.jpg';fit.save(target,'JPEG',quality=95,optimize=True)
            self.current=target;self.preview();self.apply.setEnabled(True);self.info.setText(f'Imagen detectada y ajustada a Carta: {target.name}')
        except Exception as exc:self.info.setText(f'No se pudo procesar {source.name}: {exc}')
    def preview(self):
        if not self.current:return
        pm=QPixmap(str(self.current))
        if not pm.isNull():self.sheet.setPixmap(pm.scaled(self.sheet.contentsRect().size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def resizeEvent(self,event):super().resizeEvent(event);QTimer.singleShot(0,self.preview)
    def apply_image(self):
        if self.current:self.image_applied.emit(str(self.current));self.hide()
    def closeEvent(self,event):event.ignore();self.hide()
