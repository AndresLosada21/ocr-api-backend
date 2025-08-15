"""
Serviço para leitura de códigos QR usando OpenCV e pyzbar.
"""
from typing import List, Dict, Any
import logging
import cv2
from pyzbar.pyzbar import decode
import numpy as np
from app.utils.exceptions import OCRAPIException

logger = logging.getLogger(__name__)

class QRCodeService:
    """
    Classe para gerenciar a leitura de códigos QR.
    """
    
    def __init__(self):
        """Inicializa o serviço de QR Code."""
        logger.info("QRCodeService inicializado com sucesso")
    
    def read_qrcodes(self, image_path: str, multiple: bool = True) -> Dict[str, Any]:
        """
        Lê códigos QR em uma imagem.
        
        Args:
            image_path: Caminho para o arquivo de imagem.
            multiple: Se True, detecta múltiplos QR codes.
        
        Returns:
            Dict com QR codes encontrados: data, bbox, etc.
        
        Raises:
            OCRAPIException: Em caso de falha na leitura.
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise OCRAPIException(
                    status_code=400,
                    error_code="INVALID_IMAGE",
                    message="Não foi possível carregar a imagem"
                )
            
            # Converter para grayscale para melhor detecção
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            decoded_objects = decode(gray)
            
            if not decoded_objects:
                raise OCRAPIException(
                    status_code=404,
                    error_code="NO_QRCODE_DETECTED",
                    message="Nenhum código QR detectado na imagem"
                )
            
            qrcodes = []
            for obj in decoded_objects:
                if obj.type != 'QRCODE':
                    continue
                qrcodes.append({
                    "data": obj.data.decode('utf-8'),
                    "bbox": [obj.rect.left, obj.rect.top, obj.rect.width, obj.rect.height],
                    "quality": obj.quality
                })
                if not multiple:
                    break
            
            return {
                "qr_codes": qrcodes,
                "count": len(qrcodes)
            }
        
        except Exception as e:
            logger.error("Erro ao ler códigos QR", extra={"error": str(e), "image_path": image_path})
            raise OCRAPIException(
                status_code=500,
                error_code="QRCODE_PROCESSING_ERROR",
                message="Falha ao processar a imagem para códigos QR",
                details=str(e)
            )