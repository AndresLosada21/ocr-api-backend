"""
Serviço principal para processamento de OCR usando PaddleOCR.
Responsável por inicializar o modelo e processar imagens.
"""
from typing import List, Dict, Any, Optional
import logging
import cv2
from paddleocr import PaddleOCR
import numpy as np
from app.config.settings import settings
from app.utils.exceptions import OCRAPIException  # Assumindo que exceptions.py existe; se não, crie com classe base

logger = logging.getLogger(__name__)

class OCRService:
    """
    Classe para gerenciar o serviço de OCR com PaddleOCR.
    
    Attributes:
        paddle_ocr: Instância do PaddleOCR inicializada.
        supported_languages: Lista de idiomas suportados.
    """
    
    def __init__(self):
        """Inicializa o serviço OCR com configurações do PaddleOCR."""
        try:
            self.paddle_ocr = PaddleOCR(
                use_angle_cls=settings.PADDLE_OCR_USE_ANGLE_CLS,
                lang=settings.PADDLE_OCR_LANG,
                use_gpu=settings.PADDLE_OCR_USE_GPU,
                use_space_char=settings.PADDLE_OCR_USE_SPACE_CHAR,
                det=settings.PADDLE_OCR_DET,
                rec=settings.PADDLE_OCR_REC,
                cls=settings.PADDLE_OCR_CLS,
            )
            self.supported_languages = ['pt', 'en', 'es']  # Expanda conforme necessário
            logger.info("PaddleOCR inicializado com sucesso", extra={"lang": settings.PADDLE_OCR_LANG})
        except Exception as e:
            logger.error("Falha ao inicializar PaddleOCR", extra={"error": str(e)})
            raise OCRAPIException(
                status_code=500,
                error_code="OCR_INIT_ERROR",
                message="Falha ao inicializar o serviço de OCR",
                details=str(e)
            )
    
    def process_image(self, image_path: str, language: str = 'pt', return_confidence: bool = False) -> Dict[str, Any]:
        """
        Processa uma imagem para extrair texto via OCR.
        
        Args:
            image_path: Caminho para o arquivo de imagem.
            language: Idioma para reconhecimento (default: 'pt').
            return_confidence: Se True, inclui confiança nos resultados.
        
        Returns:
            Dict com resultados do OCR: full_text, text_blocks, etc.
        
        Raises:
            OCRAPIException: Em caso de falha no processamento.
        """
        if language not in self.supported_languages:
            raise OCRAPIException(
                status_code=400,
                error_code="UNSUPPORTED_LANGUAGE",
                message="Idioma não suportado",
                details=f"Idiomas disponíveis: {self.supported_languages}"
            )
        
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise OCRAPIException(
                    status_code=400,
                    error_code="INVALID_IMAGE",
                    message="Não foi possível carregar a imagem"
                )
            
            result = self.paddle_ocr.ocr(image, cls=True)
            
            if not result or not result[0]:
                raise OCRAPIException(
                    status_code=404,
                    error_code="NO_TEXT_DETECTED",
                    message="Nenhum texto detectado na imagem"
                )
            
            # Processar resultados (ajustado para formato do PaddleOCR v2.7+)
            text_blocks = []
            full_text = ""
            for idx, line in enumerate(result[0]):
                bbox, (text, confidence) = line
                block_data = {
                    "text": text,
                    "bbox": bbox
                }
                if return_confidence:
                    block_data["confidence"] = confidence
                text_blocks.append(block_data)
                full_text += text + "\n"
            
            return {
                "text_blocks": text_blocks,
                "full_text": full_text.strip(),
                "language_detected": language,
                "total_blocks": len(text_blocks)
            }
        
        except Exception as e:
            logger.error("Erro ao processar imagem com OCR", extra={"error": str(e), "image_path": image_path})
            raise OCRAPIException(
                status_code=500,
                error_code="OCR_PROCESSING_ERROR",
                message="Falha ao processar a imagem com OCR",
                details=str(e)
            )