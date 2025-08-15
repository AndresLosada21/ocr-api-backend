"""
Serviço para leitura de códigos de barras usando pyzbar.
Suporta EAN, CODE128, etc.
"""
from typing import List, Dict, Any, Optional
import logging
import cv2
from pyzbar.pyzbar import decode
import numpy as np
from app.utils.exceptions import OCRAPIException

logger = logging.getLogger(__name__)

class BarcodeService:
    """
    Classe para gerenciar a leitura de códigos de barras.
    
    Attributes:
        supported_types: Lista de tipos de barcode suportados.
    """
    
    def __init__(self):
        """Inicializa o serviço de barcode."""
        self.supported_types = ['EAN13', 'CODE128', 'CODE39', 'EAN8']  # Expanda conforme necessário
        logger.info("BarcodeService inicializado com sucesso")
    
    def read_barcodes(self, image_path: str, barcode_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Lê códigos de barras em uma imagem.
        
        Args:
            image_path: Caminho para o arquivo de imagem.
            barcode_types: Lista de tipos específicos para filtrar (opcional).
        
        Returns:
            Dict com barcodes encontrados: data, type, bbox, etc.
        
        Raises:
            OCRAPIException: Em caso de falha na leitura.
        """
        if barcode_types:
            for typ in barcode_types:
                if typ not in self.supported_types:
                    raise OCRAPIException(
                        status_code=400,
                        error_code="UNSUPPORTED_BARCODE_TYPE",
                        message="Tipo de barcode não suportado",
                        details=f"Tipos disponíveis: {self.supported_types}"
                    )
        
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise OCRAPIException(
                    status_code=400,
                    error_code="INVALID_IMAGE",
                    message="Não foi possível carregar a imagem"
                )
            
            decoded_objects = decode(image)
            
            if not decoded_objects:
                raise OCRAPIException(
                    status_code=404,
                    error_code="NO_BARCODE_DETECTED",
                    message="Nenhum código de barras detectado na imagem"
                )
            
            barcodes = []
            for obj in decoded_objects:
                if barcode_types and obj.type not in barcode_types:
                    continue
                barcodes.append({
                    "data": obj.data.decode('utf-8'),
                    "type": obj.type,
                    "bbox": [obj.rect.left, obj.rect.top, obj.rect.width, obj.rect.height],
                    "quality": obj.quality
                })
            
            return {
                "barcodes": barcodes,
                "count": len(barcodes)
            }
        
        except Exception as e:
            logger.error("Erro ao ler códigos de barras", extra={"error": str(e), "image_path": image_path})
            raise OCRAPIException(
                status_code=500,
                error_code="BARCODE_PROCESSING_ERROR",
                message="Falha ao processar a imagem para códigos de barras",
                details=str(e)
            )