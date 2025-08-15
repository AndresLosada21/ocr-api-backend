# app/models/database/ocr_result.py
"""
Modelo para armazenar resultados detalhados de OCR.
Complementa a tabela processing_jobs com dados específicos do OCR.
"""
from sqlalchemy import Column, String, Text, Integer, Float, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from typing import Dict, Any, List, Optional

from app.models.database.base import BaseModel

class OCRResult(BaseModel):
    """
    Modelo para resultados detalhados de OCR.
    Armazena informações específicas sobre texto extraído.
    """
    
    __tablename__ = "ocr_results"
    __table_args__ = {
        'comment': 'Resultados detalhados de processamento OCR'
    }
    
    # ======================
    # RELATIONSHIP
    # ======================
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do job de processamento relacionado"
    )
    
    # ======================
    # TEXT CONTENT
    # ======================
    full_text = Column(
        Text,
        nullable=True,
        comment="Texto completo extraído da imagem"
    )
    
    language_detected = Column(
        String(10),
        nullable=True,
        comment="Idioma detectado no texto"
    )
    
    total_blocks = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número total de blocos de texto detectados"
    )
    
    total_characters = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número total de caracteres extraídos"
    )
    
    total_words = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número total de palavras extraídas"
    )
    
    # ======================
    # CONFIDENCE METRICS
    # ======================
    confidence_avg = Column(
        Float,
        nullable=True,
        comment="Confiança média de todos os blocos (0-1)"
    )
    
    confidence_min = Column(
        Float,
        nullable=True,
        comment="Menor confiança encontrada (0-1)"
    )
    
    confidence_max = Column(
        Float,
        nullable=True,
        comment="Maior confiança encontrada (0-1)"
    )
    
    confidence_std = Column(
        Float,
        nullable=True,
        comment="Desvio padrão das confianças"
    )
    
    # ======================
    # TEXT BLOCKS DETAILS
    # ======================
    text_blocks = Column(
        JSON,
        nullable=True,
        comment="Array com todos os blocos de texto detectados"
    )
    
    blocks_with_low_confidence = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número de blocos com confiança abaixo de 0.8"
    )
    
    # ======================
    # PROCESSING DETAILS
    # ======================
    paddle_ocr_version = Column(
        String(20),
        nullable=True,
        comment="Versão do PaddleOCR utilizada"
    )
    
    model_version = Column(
        String(50),
        nullable=True,
        comment="Versão do modelo OCR utilizado"
    )
    
    preprocessing_applied = Column(
        JSON,
        nullable=True,
        comment="Lista de preprocessamentos aplicados na imagem"
    )
    
    orientation_detected = Column(
        Float,
        nullable=True,
        comment="Orientação detectada da imagem em graus"
    )
    
    orientation_corrected = Column(
        Float,
        nullable=True,
        comment="Correção de orientação aplicada em graus"
    )
    
    # ======================
    # IMAGE ANALYSIS
    # ======================
    image_quality_score = Column(
        Float,
        nullable=True,
        comment="Score de qualidade da imagem para OCR (0-1)"
    )
    
    text_density = Column(
        Float,
        nullable=True,
        comment="Densidade de texto na imagem (caracteres por pixel)"
    )
    
    dominant_font_size = Column(
        Integer,
        nullable=True,
        comment="Tamanho de fonte dominante detectado"
    )
    
    # ======================
    # LANGUAGE ANALYSIS
    # ======================
    language_confidence = Column(
        Float,
        nullable=True,
        comment="Confiança na detecção do idioma (0-1)"
    )
    
    mixed_languages = Column(
        JSON,
        nullable=True,
        comment="Array com idiomas detectados se múltiplos"
    )
    
    # ======================
    # STATISTICS
    # ======================
    sentences_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número estimado de sentenças"
    )
    
    paragraphs_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número estimado de parágrafos"
    )
    
    numeric_sequences = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número de sequências numéricas detectadas"
    )
    
    email_addresses = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número de endereços de email detectados"
    )
    
    phone_numbers = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número de telefones detectados"
    )
    
    urls_found = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número de URLs detectadas"
    )
    
    # ======================
    # RELATIONSHIP
    # ======================
    job = relationship(
        "ProcessingJob",
        back_populates="ocr_results",
        lazy="select"
    )
    
    def __init__(self, **kwargs):
        """Inicializa resultado OCR."""
        super().__init__(**kwargs)
    
    def calculate_statistics(self, text_blocks: List[Dict[str, Any]]) -> None:
        """
        Calcula estatísticas automáticas baseadas nos blocos de texto.
        
        Args:
            text_blocks: Lista de blocos de texto do OCR
        """
        if not text_blocks:
            return
        
        # Estatísticas básicas
        self.total_blocks = len(text_blocks)
        
        # Extrair todo o texto
        full_text = ""
        confidences = []
        
        for block in text_blocks:
            text = block.get("text", "")
            confidence = block.get("confidence")
            
            full_text += text + " "
            if confidence is not None:
                confidences.append(confidence)
        
        self.full_text = full_text.strip()
        self.total_characters = len(self.full_text)
        self.total_words = len(self.full_text.split()) if self.full_text else 0
        
        # Estatísticas de confiança
        if confidences:
            import statistics
            self.confidence_avg = statistics.mean(confidences)
            self.confidence_min = min(confidences)
            self.confidence_max = max(confidences)
            if len(confidences) > 1:
                self.confidence_std = statistics.stdev(confidences)
            
            # Blocos com baixa confiança
            self.blocks_with_low_confidence = len([c for c in confidences if c < 0.8])
        
        # Análise de conteúdo
        self._analyze_content()
    
    def _analyze_content(self) -> None:
        """Analisa o conteúdo do texto para extrair estatísticas."""
        if not self.full_text:
            return
        
        import re
        
        text = self.full_text
        
        # Contar sentenças (aproximado)
        sentences = re.split(r'[.!?]+', text)
        self.sentences_count = len([s for s in sentences if s.strip()])
        
        # Contar parágrafos (aproximado)
        paragraphs = text.split('\n\n')
        self.paragraphs_count = len([p for p in paragraphs if p.strip()])
        
        # Detectar emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.email_addresses = len(re.findall(email_pattern, text))
        
        # Detectar telefones (padrão brasileiro)
        phone_pattern = r'(\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}'
        self.phone_numbers = len(re.findall(phone_pattern, text))
        
        # Detectar URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        self.urls_found = len(re.findall(url_pattern, text))
        
        # Detectar sequências numéricas
        numeric_pattern = r'\b\d{4,}\b'  # 4 ou mais dígitos consecutivos
        self.numeric_sequences = len(re.findall(numeric_pattern, text))
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo das estatísticas do OCR.
        
        Returns:
            Dicionário com resumo dos dados
        """
        return {
            "total_blocks": self.total_blocks,
            "total_characters": self.total_characters,
            "total_words": self.total_words,
            "language_detected": self.language_detected,
            "confidence_avg": self.confidence_avg,
            "confidence_range": [self.confidence_min, self.confidence_max] if self.confidence_min else None,
            "low_confidence_blocks": self.blocks_with_low_confidence,
            "content_analysis": {
                "sentences": self.sentences_count,
                "paragraphs": self.paragraphs_count,
                "emails": self.email_addresses,
                "phones": self.phone_numbers,
                "urls": self.urls_found,
                "numeric_sequences": self.numeric_sequences
            },
            "processing_info": {
                "paddle_ocr_version": self.paddle_ocr_version,
                "model_version": self.model_version,
                "orientation_corrected": self.orientation_corrected
            }
        }
    
    def to_dict(self, include_text_blocks: bool = False) -> Dict[str, Any]:
        """
        Converte para dicionário com opção de incluir blocos de texto.
        
        Args:
            include_text_blocks: Se deve incluir array completo de text_blocks
            
        Returns:
            Dicionário com dados do modelo
        """
        exclude_fields = set()
        if not include_text_blocks:
            exclude_fields.add("text_blocks")
        
        return super().to_dict(exclude_fields=exclude_fields)
    
    def __repr__(self) -> str:
        """Representação string do resultado OCR."""
        return f"<OCRResult(job_id={self.job_id}, blocks={self.total_blocks}, chars={self.total_characters})>"