
"""
PDF Görsel Ayıklayıcı - Web Arayüzü
Modern ve kullanıcı dostu web arayüzü ile PDF'lerden görsel ayıklama
"""

import os
import tempfile
import zipfile
from pathlib import Path
import fitz  # PyMuPDF
import gradio as gr
from PIL import Image
import io


def extract_images_from_pdf(pdf_file):
    """
    PDF dosyasından tüm görselleri ayıklar ve ZIP dosyası olarak döndürür.
    
    Args:
        pdf_file: Yüklenen PDF dosyası
    
    Returns:
        tuple: (ZIP dosya yolu, mesaj, görsel listesi)
    """
    if pdf_file is None:
        return None, "Lütfen bir PDF dosyası yükleyin!", []
    
    try:
        # PDF'i aç
        pdf_document = fitz.open(pdf_file.name)
        pdf_name = Path(pdf_file.name).stem
        
        # Geçici dizin oluştur
        temp_dir = tempfile.mkdtemp()
        image_paths = []
        image_count = 0
        
        status_messages = []
        status_messages.append(f"PDF: {pdf_name}")
        status_messages.append(f"Toplam sayfa: {len(pdf_document)}\n")
        
        # Her sayfayı işle
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            
            if image_list:
                status_messages.append(f"Sayfa {page_num + 1}: {len(image_list)} görsel bulundu")
            
            # Sayfadaki her görseli kaydet
            for image_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    # Görsel verisini al
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Dosya adı oluştur
                    image_filename = f"{pdf_name}_sayfa{page_num + 1}_gorsel{image_index + 1}.{image_ext}"
                    image_path = os.path.join(temp_dir, image_filename)
                    
                    # Görseli kaydet
                    with open(image_path, "wb") as image_file:
                        image_file.write(image_bytes)
                    
                    image_paths.append(image_path)
                    image_count += 1
                    status_messages.append(f"  {image_filename}")
                    
                except Exception as e:
                    status_messages.append(f"  Görsel {image_index + 1} ayıklanamadı: {e}")
        
        pdf_document.close()
        
        if image_count == 0:
            return None, "PDF'de görsel bulunamadı!", []
        
        # ZIP dosyası oluştur
        zip_path = os.path.join(temp_dir, f"{pdf_name}_gorseller.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for img_path in image_paths:
                zipf.write(img_path, os.path.basename(img_path))
        
        status_messages.append(f"\nTamamlandı! Toplam {image_count} görsel ayıklandı.")
        status_messages.append(f"ZIP dosyası hazır: {image_count} görsel")
        
        # Önizleme için görsel listesi (maksimum 20 görsel)
        preview_images = []
        for img_path in image_paths[:20]:
            try:
                preview_images.append(Image.open(img_path))
            except:
                pass
        
        return zip_path, "\n".join(status_messages), preview_images
        
    except Exception as e:
        return None, f"Hata oluştu: {str(e)}", []


def create_ui():
    """Gradio arayüzünü oluşturur"""
    
    custom_css = """
    .primary-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
    }
    .primary-btn:hover {
        background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%) !important;
    }
    """
    
    with gr.Blocks(title="PDF Görsel Ayıklayıcı", css=custom_css) as app:
        gr.Markdown(
            """
            <h1 style="text-align: center; font-size: 3em; margin-bottom: 0.5em; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">PDF Görsel Ayıklayıcı</h1>
            <p style="text-align: center; font-size: 1.2em; color: #666;">PDF dosyalarınızdaki tüm görselleri kolayca ayıklayın ve indirin.</p>
            """
        )
        
        # Dosya yükleme alanı (her zaman görünür)
        pdf_input = gr.File(
            label="PDF Dosyası Yükleyin",
            file_types=[".pdf"],
            type="filepath"
        )
        
        # İşlem butonu (dosya yüklenince görünür)
        extract_btn = gr.Button(
            "Görselleri Ayıkla",
            variant="primary",
            size="lg",
            visible=False,
            elem_classes="primary-btn"
        )
        
        # Sonuç alanları (başlangıçta gizli)
        with gr.Row(visible=False) as results_row:
            with gr.Column(scale=1):
                # Durum mesajları
                status_output = gr.Textbox(
                    label="İşlem Durumu",
                    lines=10,
                    max_lines=15,
                    interactive=False
                )
                
                # İndirme butonu
                download_output = gr.File(
                    label="İndirme",
                    interactive=False
                )
            
            with gr.Column(scale=1):
                # Görsel önizleme
                gr.Markdown("### Görsel Önizleme")
                gr.Markdown("*İlk 20 görsel gösterilir*")
                
                gallery_output = gr.Gallery(
                    label="Ayıklanan Görseller",
                    columns=3,
                    rows=3,
                    height="auto",
                    object_fit="contain"
                )
        
        # Dosya yüklenince butonu göster
        def show_extract_button(file):
            if file is not None:
                return gr.Button(visible=True)
            return gr.Button(visible=False)
        
        # İşlem tamamlanınca sonuçları göster
        def process_and_show(pdf_file):
            zip_file, status, images = extract_images_from_pdf(pdf_file)
            return (
                zip_file,
                status,
                images,
                gr.Row(visible=True)  # Sonuç alanını göster
            )
        
        # Olay dinleyicileri
        pdf_input.change(
            fn=show_extract_button,
            inputs=[pdf_input],
            outputs=[extract_btn]
        )
        
        extract_btn.click(
            fn=process_and_show,
            inputs=[pdf_input],
            outputs=[download_output, status_output, gallery_output, results_row]
        )
    
    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch(
        server_name="127.0.0.1",
        share=False,
        show_error=True,
        inbrowser=True
    )
