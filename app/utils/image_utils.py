# app/utils/image_utils.py
"""
Utilitários para processamento e manipulação de imagens.
Funcionalidades de redimensionamento, rotação, melhoria de qualidade.
"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Tuple, Optional, Dict, Any
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

class ImageUtils:
    """Classe com utilitários para processamento de imagens."""
    
    @staticmethod
    def load_image(image_path: str) -> np.ndarray:
        """
        Carrega imagem como array NumPy.
        
        Args:
            image_path: Caminho da imagem
            
        Returns:
            Array NumPy da imagem
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Não foi possível carregar a imagem: {image_path}")
            return image
        except Exception as e:
            logger.error(f"Erro ao carregar imagem {image_path}: {str(e)}")
            raise
    
    @staticmethod
    def save_image(image: np.ndarray, output_path: str) -> None:
        """
        Salva array NumPy como imagem.
        
        Args:
            image: Array NumPy da imagem
            output_path: Caminho de saída
        """
        try:
            cv2.imwrite(output_path, image)
        except Exception as e:
            logger.error(f"Erro ao salvar imagem {output_path}: {str(e)}")
            raise
    
    @staticmethod
    def resize_image(
        image: np.ndarray, 
        max_width: int = None, 
        max_height: int = None,
        maintain_aspect: bool = True
    ) -> np.ndarray:
        """
        Redimensiona imagem mantendo proporção.
        
        Args:
            image: Array NumPy da imagem
            max_width: Largura máxima
            max_height: Altura máxima
            maintain_aspect: Se deve manter proporção
            
        Returns:
            Imagem redimensionada
        """
        height, width = image.shape[:2]
        
        if max_width is None:
            max_width = settings.MAX_IMAGE_DIMENSION
        if max_height is None:
            max_height = settings.MAX_IMAGE_DIMENSION
        
        if width <= max_width and height <= max_height:
            return image
        
        if maintain_aspect:
            # Calcular escala mantendo proporção
            scale_w = max_width / width
            scale_h = max_height / height
            scale = min(scale_w, scale_h)
            
            new_width = int(width * scale)
            new_height = int(height * scale)
        else:
            new_width = max_width
            new_height = max_height
        
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        logger.debug(f"Imagem redimensionada: {width}x{height} -> {new_width}x{new_height}")
        return resized
    
    @staticmethod
    def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
        """
        Aplica melhorias específicas para OCR.
        
        Args:
            image: Array NumPy da imagem
            
        Returns:
            Imagem otimizada para OCR
        """
        # Converter para escala de cinza se colorida
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Equalização do histograma
        equalized = cv2.equalizeHist(denoised)
        
        # Sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(equalized, -1, kernel)
        
        # Threshold adaptativo para binarização
        binary = cv2.adaptiveThreshold(
            sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Converter de volta para BGR se necessário
        if len(image.shape) == 3:
            enhanced = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        else:
            enhanced = binary
        
        logger.debug("Melhorias para OCR aplicadas")
        return enhanced
    
    @staticmethod
    def enhance_for_barcode(image: np.ndarray) -> np.ndarray:
        """
        Aplica melhorias específicas para leitura de códigos de barras.
        
        Args:
            image: Array NumPy da imagem
            
        Returns:
            Imagem otimizada para códigos de barras
        """
        # Converter para escala de cinza
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Denoising suave
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Aumentar contraste
        enhanced = cv2.convertScaleAbs(denoised, alpha=1.2, beta=10)
        
        # Threshold para binarização
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Operações morfológicas para limpar ruído
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Converter de volta para BGR se necessário
        if len(image.shape) == 3:
            result = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
        else:
            result = cleaned
        
        logger.debug("Melhorias para códigos de barras aplicadas")
        return result
    
    @staticmethod
    def detect_and_correct_orientation(image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detecta e corrige orientação da imagem.
        
        Args:
            image: Array NumPy da imagem
            
        Returns:
            Tupla com (imagem_corrigida, ângulo_aplicado)
        """
        # Converter para escala de cinza
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Detectar linhas usando Hough Transform
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is not None:
            # Calcular ângulos das linhas
            angles = []
            for rho, theta in lines[:20]:  # Usar apenas as primeiras 20 linhas
                angle = np.rad2deg(theta) - 90
                angles.append(angle)
            
            # Encontrar ângulo mais comum
            if angles:
                angle = np.median(angles)
                
                # Corrigir apenas se o ângulo for significativo
                if abs(angle) > 1:
                    # Rotacionar imagem
                    center = (image.shape[1] // 2, image.shape[0] // 2)
                    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                    corrected = cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))
                    
                    logger.debug(f"Orientação corrigida: {angle:.2f}°")
                    return corrected, angle
        
        return image, 0.0
    
    @staticmethod
    def improve_contrast(image: np.ndarray, method: str = "clahe") -> np.ndarray:
        """
        Melhora contraste da imagem.
        
        Args:
            image: Array NumPy da imagem
            method: Método a usar (clahe, histogram, gamma)
            
        Returns:
            Imagem com contraste melhorado
        """
        if len(image.shape) == 3:
            # Para imagens coloridas, trabalhar no espaço LAB
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]
        else:
            l_channel = image.copy()
        
        if method == "clahe":
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(l_channel)
        elif method == "histogram":
            # Equalização simples do histograma
            enhanced = cv2.equalizeHist(l_channel)
        elif method == "gamma":
            # Correção gamma
            gamma = 1.2
            enhanced = np.power(l_channel / 255.0, gamma) * 255
            enhanced = enhanced.astype(np.uint8)
        else:
            enhanced = l_channel
        
        if len(image.shape) == 3:
            # Recombinar canais
            lab[:, :, 0] = enhanced
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            result = enhanced
        
        logger.debug(f"Contraste melhorado usando método: {method}")
        return result
    
    @staticmethod
    def remove_noise(image: np.ndarray, method: str = "bilateral") -> np.ndarray:
        """
        Remove ruído da imagem.
        
        Args:
            image: Array NumPy da imagem
            method: Método de denoising
            
        Returns:
            Imagem sem ruído
        """
        if method == "bilateral":
            if len(image.shape) == 3:
                denoised = cv2.bilateralFilter(image, 9, 75, 75)
            else:
                denoised = cv2.bilateralFilter(image, 9, 75, 75)
        elif method == "gaussian":
            denoised = cv2.GaussianBlur(image, (5, 5), 0)
        elif method == "median":
            denoised = cv2.medianBlur(image, 5)
        elif method == "nlmeans":
            if len(image.shape) == 3:
                denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
            else:
                denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        else:
            denoised = image
        
        logger.debug(f"Ruído removido usando método: {method}")
        return denoised
    
    @staticmethod
    def sharpen_image(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Aplica sharpening na imagem.
        
        Args:
            image: Array NumPy da imagem
            strength: Força do sharpening (0.5 a 2.0)
            
        Returns:
            Imagem com sharpening aplicado
        """
        # Kernel de sharpening
        kernel = np.array([
            [-1, -1, -1],
            [-1, 8 + strength, -1],
            [-1, -1, -1]
        ])
        
        sharpened = cv2.filter2D(image, -1, kernel)
        
        logger.debug(f"Sharpening aplicado com força: {strength}")
        return sharpened
    
    @staticmethod
    def crop_to_content(image: np.ndarray, padding: int = 10) -> np.ndarray:
        """
        Corta imagem removendo bordas desnecessárias.
        
        Args:
            image: Array NumPy da imagem
            padding: Padding a manter em pixels
            
        Returns:
            Imagem cortada
        """
        # Converter para escala de cinza
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Threshold para encontrar conteúdo
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Encontrar bounding box de todos os contornos
            all_contours = np.vstack(contours)
            x, y, w, h = cv2.boundingRect(all_contours)
            
            # Adicionar padding
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(image.shape[1] - x, w + 2 * padding)
            h = min(image.shape[0] - y, h + 2 * padding)
            
            # Cortar imagem
            cropped = image[y:y+h, x:x+w]
            
            logger.debug(f"Imagem cortada: {image.shape} -> {cropped.shape}")
            return cropped
        
        return image
    
    @staticmethod
    def get_image_quality_score(image: np.ndarray) -> float:
        """
        Calcula score de qualidade da imagem.
        
        Args:
            image: Array NumPy da imagem
            
        Returns:
            Score de qualidade (0.0 a 1.0)
        """
        # Converter para escala de cinza se necessário
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Calcular variância (nitidez)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(1.0, laplacian_var / 1000)  # Normalizar
        
        # Calcular contraste
        contrast = gray.std()
        contrast_score = min(1.0, contrast / 64)  # Normalizar
        
        # Calcular brilho (deve estar em uma faixa adequada)
        brightness = gray.mean()
        if 50 <= brightness <= 200:
            brightness_score = 1.0
        else:
            brightness_score = max(0.0, 1.0 - abs(brightness - 125) / 125)
        
        # Score final combinado
        quality_score = (
            sharpness_score * 0.4 + 
            contrast_score * 0.3 + 
            brightness_score * 0.3
        )
        
        logger.debug(f"Score de qualidade: {quality_score:.3f} (nitidez: {sharpness_score:.3f}, contraste: {contrast_score:.3f}, brilho: {brightness_score:.3f})")
        return quality_score
    
    @staticmethod
    def analyze_image_properties(image: np.ndarray) -> Dict[str, Any]:
        """
        Analisa propriedades da imagem.
        
        Args:
            image: Array NumPy da imagem
            
        Returns:
            Dicionário com propriedades da imagem
        """
        height, width = image.shape[:2]
        
        # Converter para escala de cinza se necessário
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            is_color = True
            channels = 3
        else:
            gray = image.copy()
            is_color = False
            channels = 1
        
        # Propriedades básicas
        properties = {
            "dimensions": {"width": width, "height": height},
            "channels": channels,
            "is_color": is_color,
            "total_pixels": width * height,
            "aspect_ratio": round(width / height, 2) if height > 0 else 0
        }
        
        # Análise de brilho e contraste
        mean_brightness = float(gray.mean())
        std_brightness = float(gray.std())
        
        properties.update({
            "brightness": {
                "mean": mean_brightness,
                "std": std_brightness,
                "min": int(gray.min()),
                "max": int(gray.max())
            }
        })
        
        # Análise de nitidez
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        properties["sharpness"] = {
            "laplacian_variance": float(laplacian_var),
            "is_blurry": laplacian_var < 100
        }
        
        # Detecção de bordas
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / (width * height)
        properties["edges"] = {
            "density": float(edge_density),
            "total_edge_pixels": int(np.sum(edges > 0))
        }
        
        # Score de qualidade geral
        properties["quality_score"] = ImageUtils.get_image_quality_score(image)
        
        return properties
    
    @staticmethod
    def apply_preprocessing_pipeline(
        image: np.ndarray, 
        for_ocr: bool = False,
        for_barcode: bool = False,
        auto_enhance: bool = True
    ) -> np.ndarray:
        """
        Aplica pipeline completo de pré-processamento.
        
        Args:
            image: Array NumPy da imagem
            for_ocr: Se deve otimizar para OCR
            for_barcode: Se deve otimizar para códigos de barras
            auto_enhance: Se deve aplicar melhorias automáticas
            
        Returns:
            Imagem pré-processada
        """
        processed = image.copy()
        
        # Redimensionar se necessário
        processed = ImageUtils.resize_image(processed)
        
        # Detectar e corrigir orientação
        if auto_enhance:
            processed, angle = ImageUtils.detect_and_correct_orientation(processed)
        
        # Aplicar otimizações específicas
        if for_ocr:
            processed = ImageUtils.enhance_for_ocr(processed)
        elif for_barcode:
            processed = ImageUtils.enhance_for_barcode(processed)
        elif auto_enhance:
            # Melhorias gerais
            processed = ImageUtils.remove_noise(processed, method="bilateral")
            processed = ImageUtils.improve_contrast(processed, method="clahe")
            processed = ImageUtils.sharpen_image(processed, strength=0.5)
        
        logger.info("Pipeline de pré-processamento aplicado", extra={
            "for_ocr": for_ocr,
            "for_barcode": for_barcode,
            "auto_enhance": auto_enhance
        })
        
        return processed

# Funções utilitárias convenientes
def enhance_image_for_ocr(image_path: str, output_path: str = None) -> str:
    """
    Melhora imagem especificamente para OCR.
    
    Args:
        image_path: Caminho da imagem original
        output_path: Caminho de saída (opcional)
        
    Returns:
        Caminho da imagem processada
    """
    image = ImageUtils.load_image(image_path)
    enhanced = ImageUtils.enhance_for_ocr(image)
    
    if output_path is None:
        output_path = image_path.replace('.', '_enhanced_ocr.')
    
    ImageUtils.save_image(enhanced, output_path)
    return output_path

def enhance_image_for_barcode(image_path: str, output_path: str = None) -> str:
    """
    Melhora imagem especificamente para códigos de barras.
    
    Args:
        image_path: Caminho da imagem original
        output_path: Caminho de saída (opcional)
        
    Returns:
        Caminho da imagem processada
    """
    image = ImageUtils.load_image(image_path)
    enhanced = ImageUtils.enhance_for_barcode(image)
    
    if output_path is None:
        output_path = image_path.replace('.', '_enhanced_barcode.')
    
    ImageUtils.save_image(enhanced, output_path)
    return output_path

def get_image_quality(image_path: str) -> float:
    """
    Retorna score de qualidade da imagem.
    
    Args:
        image_path: Caminho da imagem
        
    Returns:
        Score de qualidade (0.0 a 1.0)
    """
    image = ImageUtils.load_image(image_path)
    return ImageUtils.get_image_quality_score(image)

def analyze_image(image_path: str) -> Dict[str, Any]:
    """
    Analisa propriedades completas da imagem.
    
    Args:
        image_path: Caminho da imagem
        
    Returns:
        Dicionário com análise completa
    """
    image = ImageUtils.load_image(image_path)
    return ImageUtils.analyze_image_properties(image)