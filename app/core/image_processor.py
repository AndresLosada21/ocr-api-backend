"""
Processador de imagens para validação, redimensionamento e pré-processamento.
Usa OpenCV para manipulação.
"""
from typing import Optional
import logging
import cv2
import numpy as np
from app.config.settings import settings
from app.utils.exceptions import OCRAPIException

logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Classe para processar e validar imagens antes do uso nos serviços.
    """
    
    def __init__(self):
        """Inicializa o processador de imagens."""
        logger.info("ImageProcessor inicializado com sucesso")
    
    def validate_image(self, image: np.ndarray) -> None:
        """
        Valida dimensões e qualidade da imagem.
        
        Args:
            image: Array NumPy da imagem.
        
        Raises:
            OCRAPIException: Se a imagem for inválida.
        """
        height, width = image.shape[:2]
        
        if height < settings.MIN_IMAGE_DIMENSION or width < settings.MIN_IMAGE_DIMENSION:
            raise OCRAPIException(
                status_code=400,
                error_code="IMAGE_TOO_SMALL",
                message="Imagem muito pequena",
                details=f"Dimensões mínimas: {settings.MIN_IMAGE_DIMENSION}x{settings.MIN_IMAGE_DIMENSION}"
            )
        
        if height > settings.MAX_IMAGE_DIMENSION or width > settings.MAX_IMAGE_DIMENSION:
            raise OCRAPIException(
                status_code=400,
                error_code="IMAGE_TOO_LARGE",
                message="Imagem muito grande",
                details=f"Dimensões máximas: {settings.MAX_IMAGE_DIMENSION}x{settings.MAX_IMAGE_DIMENSION}"
            )
    
    def resize_image(self, image: np.ndarray, max_dimension: int = settings.MAX_IMAGE_DIMENSION) -> np.ndarray:
        """
        Redimensiona a imagem se necessário, mantendo aspect ratio.
        
        Args:
            image: Array NumPy da imagem.
            max_dimension: Dimensão máxima permitida.
        
        Returns:
            Imagem redimensionada.
        """
        height, width = image.shape[:2]
        if max(height, width) <= max_dimension:
            return image
        
        scale = max_dimension / max(height, width)
        new_height = int(height * scale)
        new_width = int(width * scale)
        
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        logger.info("Imagem redimensionada", extra={"original": (width, height), "new": (new_width, new_height)})
        return resized
    
    def enhance_image(self, image: np.ndarray) -> np.ndarray:
        """
        Aplica melhorias básicas na imagem (contraste, sharpening).
        
        Args:
            image: Array NumPy da imagem.
        
        Returns:
            Imagem aprimorada.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        equalized = cv2.equalizeHist(gray)
        enhanced = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)
        
        # Sharpening kernel
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        logger.info("Melhorias aplicadas na imagem")
        return sharpened
    
    def load_and_process(self, image_path: str, enhance: bool = True, resize: bool = True) -> np.ndarray:
        """
        Carrega, valida e processa a imagem.
        
        Args:
            image_path: Caminho para o arquivo.
            enhance: Aplicar enhancement.
            resize: Redimensionar se necessário.
        
        Returns:
            Imagem processada como np.ndarray.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise OCRAPIException(
                status_code=400,
                error_code="INVALID_IMAGE",
                message="Não foi possível carregar a imagem"
            )
        
        self.validate_image(image)
        
        if resize:
            image = self.resize_image(image)
        
        if enhance:
            image = self.enhance_image(image)
        
        return image