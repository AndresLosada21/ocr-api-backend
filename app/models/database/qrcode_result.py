# app/models/database/qrcode_result.py
"""
Modelo para armazenar resultados detalhados de leitura de códigos QR.
Complementa a tabela processing_jobs com dados específicos de QR codes.
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from typing import Dict, Any, List, Optional
import re
import json

from app.models.database.base import BaseModel

class QRCodeResult(BaseModel):
    """
    Modelo para resultados detalhados de leitura de códigos QR.
    Armazena informações específicas sobre cada QR code encontrado.
    """
    
    __tablename__ = "qrcode_results"
    __table_args__ = {
        'comment': 'Resultados detalhados de leitura de códigos QR'
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
    # QR CODE DATA
    # ======================
    qr_data = Column(
        Text,
        nullable=False,
        comment="Dados decodificados do código QR"
    )
    
    data_type = Column(
        String(20),
        nullable=True,
        comment="Tipo de dados: url, text, email, phone, wifi, etc."
    )
    
    data_length = Column(
        Integer,
        nullable=False,
        comment="Comprimento dos dados decodificados"
    )
    
    encoding = Column(
        String(20),
        nullable=True,
        comment="Codificação dos dados (UTF-8, etc.)"
    )
    
    # ======================
    # QR CODE PROPERTIES
    # ======================
    error_correction_level = Column(
        String(10),
        nullable=True,
        comment="Nível de correção de erro: L, M, Q, H"
    )
    
    version = Column(
        Integer,
        nullable=True,
        comment="Versão do QR code (1-40)"
    )
    
    mask_pattern = Column(
        Integer,
        nullable=True,
        comment="Padrão de máscara utilizado (0-7)"
    )
    
    data_capacity = Column(
        Integer,
        nullable=True,
        comment="Capacidade total de dados da versão"
    )
    
    data_utilization = Column(
        Float,
        nullable=True,
        comment="Percentual de utilização da capacidade (0-1)"
    )
    
    # ======================
    # POSITION AND SIZE
    # ======================
    bbox = Column(
        JSON,
        nullable=True,
        comment="Coordenadas da bounding box [x, y, width, height]"
    )
    
    center_x = Column(
        Integer,
        nullable=True,
        comment="Coordenada X do centro do QR code"
    )
    
    center_y = Column(
        Integer,
        nullable=True,
        comment="Coordenada Y do centro do QR code"
    )
    
    width = Column(
        Integer,
        nullable=True,
        comment="Largura do QR code em pixels"
    )
    
    height = Column(
        Integer,
        nullable=True,
        comment="Altura do QR code em pixels"
    )
    
    module_size = Column(
        Float,
        nullable=True,
        comment="Tamanho de cada módulo em pixels"
    )
    
    modules_count = Column(
        Integer,
        nullable=True,
        comment="Número total de módulos (version * 21 + 17)"
    )
    
    # ======================
    # QUALITY METRICS
    # ======================
    quality_score = Column(
        Float,
        nullable=True,
        comment="Score de qualidade da leitura (0-1)"
    )
    
    quality_description = Column(
        String(20),
        nullable=True,
        comment="Descrição da qualidade: excellent, good, fair, poor"
    )
    
    read_confidence = Column(
        Float,
        nullable=True,
        comment="Confiança na leitura dos dados (0-1)"
    )
    
    decode_attempts = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Número de tentativas de decodificação"
    )
    
    # ======================
    # GEOMETRIC ANALYSIS
    # ======================
    orientation = Column(
        Float,
        nullable=True,
        comment="Orientação do QR code em graus"
    )
    
    skew_angle = Column(
        Float,
        nullable=True,
        comment="Ângulo de inclinação detectado"
    )
    
    perspective_distortion = Column(
        Float,
        nullable=True,
        comment="Distorção de perspectiva detectada"
    )
    
    finder_patterns_detected = Column(
        Integer,
        nullable=True,
        comment="Número de padrões de localização detectados (0-3)"
    )
    
    timing_patterns_valid = Column(
        Boolean,
        nullable=True,
        comment="Se os padrões de timing estão válidos"
    )
    
    # ======================
    # CONTENT ANALYSIS
    # ======================
    url_info = Column(
        JSON,
        nullable=True,
        comment="Informações da URL se data_type for url"
    )
    
    wifi_info = Column(
        JSON,
        nullable=True,
        comment="Informações WiFi se data_type for wifi"
    )
    
    contact_info = Column(
        JSON,
        nullable=True,
        comment="Informações de contato se data_type for vcard"
    )
    
    geo_info = Column(
        JSON,
        nullable=True,
        comment="Informações geográficas se data_type for geo"
    )
    
    # ======================
    # PROCESSING DETAILS
    # ======================
    decoder_used = Column(
        String(50),
        nullable=True,
        comment="Biblioteca/decoder utilizado"
    )
    
    preprocessing_applied = Column(
        JSON,
        nullable=True,
        comment="Preprocessamentos aplicados para melhorar leitura"
    )
    
    error_correction_used = Column(
        Boolean,
        nullable=True,
        comment="Se correção de erro foi utilizada"
    )
    
    errors_corrected = Column(
        Integer,
        nullable=True,
        comment="Número de erros corrigidos automaticamente"
    )
    
    # ======================
    # SECURITY ANALYSIS
    # ======================
    suspicious_content = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Se o conteúdo pode ser suspeito"
    )
    
    url_shortener_detected = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Se detectou URL encurtadora"
    )
    
    security_flags = Column(
        JSON,
        nullable=True,
        comment="Flags de segurança identificadas"
    )
    
    # ======================
    # RELATIONSHIP
    # ======================
    job = relationship(
        "ProcessingJob",
        back_populates="qrcode_results",
        lazy="select"
    )
    
    def __init__(self, **kwargs):
        """Inicializa resultado de QR code."""
        super().__init__(**kwargs)
        self._calculate_derived_fields()
    
    def _calculate_derived_fields(self) -> None:
        """Calcula campos derivados automaticamente."""
        # Calcular comprimento dos dados
        if self.qr_data:
            self.data_length = len(self.qr_data)
        
        # Calcular posição central se bbox disponível
        if self.bbox and len(self.bbox) >= 4:
            x, y, w, h = self.bbox
            self.center_x = int(x + w / 2)
            self.center_y = int(y + h / 2)
            self.width = int(w)
            self.height = int(h)
        
        # Calcular módulos se versão conhecida
        if self.version:
            self.modules_count = (self.version * 4) + 17
            if self.width and self.modules_count:
                self.module_size = self.width / self.modules_count
        
        # Calcular utilização de capacidade
        if self.version and self.data_length:
            capacities = self._get_version_capacities()
            if self.version in capacities:
                max_capacity = capacities[self.version].get(self.error_correction_level, 0)
                if max_capacity > 0:
                    self.data_utilization = min(1.0, self.data_length / max_capacity)
        
        # Analisar conteúdo
        self._analyze_content()
        self._analyze_security()
    
    def _get_version_capacities(self) -> Dict[int, Dict[str, int]]:
        """Retorna capacidades por versão e nível de correção."""
        # Capacidades para caracteres alfanuméricos (simplificado)
        return {
            1: {"L": 25, "M": 20, "Q": 16, "H": 10},
            2: {"L": 47, "M": 38, "Q": 29, "H": 20},
            3: {"L": 77, "M": 61, "Q": 47, "H": 35},
            # ... mais versões conforme necessário
        }
    
    def _analyze_content(self) -> None:
        """Analisa o conteúdo do QR code para extrair informações."""
        if not self.qr_data:
            return
        
        data = self.qr_data.strip()
        
        # Determinar tipo de conteúdo
        if self._is_url(data):
            self.data_type = "url"
            self._analyze_url(data)
        elif self._is_email(data):
            self.data_type = "email"
        elif self._is_phone(data):
            self.data_type = "phone"
        elif self._is_wifi(data):
            self.data_type = "wifi"
            self._analyze_wifi(data)
        elif self._is_geo(data):
            self.data_type = "geo"
            self._analyze_geo(data)
        elif self._is_vcard(data):
            self.data_type = "vcard"
            self._analyze_vcard(data)
        elif self._is_sms(data):
            self.data_type = "sms"
        else:
            self.data_type = "text"
    
    def _is_url(self, data: str) -> bool:
        """Verifica se é uma URL."""
        return data.lower().startswith(('http://', 'https://', 'www.'))
    
    def _is_email(self, data: str) -> bool:
        """Verifica se é um email."""
        return data.startswith('mailto:') or '@' in data and '.' in data
    
    def _is_phone(self, data: str) -> bool:
        """Verifica se é um telefone."""
        return data.startswith('tel:') or data.startswith('sms:')
    
    def _is_wifi(self, data: str) -> bool:
        """Verifica se é configuração WiFi."""
        return data.upper().startswith('WIFI:')
    
    def _is_geo(self, data: str) -> bool:
        """Verifica se é localização geográfica."""
        return data.lower().startswith('geo:')
    
    def _is_vcard(self, data: str) -> bool:
        """Verifica se é um vCard."""
        return data.upper().startswith('BEGIN:VCARD')
    
    def _is_sms(self, data: str) -> bool:
        """Verifica se é SMS."""
        return data.startswith('sms:')
    
    def _analyze_url(self, data: str) -> None:
        """Analisa URL para extrair informações."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(data)
            
            self.url_info = {
                "scheme": parsed.scheme,
                "domain": parsed.netloc,
                "path": parsed.path,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "is_secure": parsed.scheme == "https"
            }
        except Exception:
            self.url_info = {"error": "Invalid URL format"}
    
    def _analyze_wifi(self, data: str) -> None:
        """Analisa configuração WiFi."""
        try:
            # Formato: WIFI:T:WPA;S:NetworkName;P:Password;H:hidden;;
            parts = data.split(';')
            wifi_data = {}
            
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    wifi_data[key] = value
            
            self.wifi_info = {
                "security_type": wifi_data.get("T", ""),
                "network_name": wifi_data.get("S", ""),
                "password_protected": bool(wifi_data.get("P", "")),
                "hidden": wifi_data.get("H", "").lower() == "true"
            }
        except Exception:
            self.wifi_info = {"error": "Invalid WiFi format"}
    
    def _analyze_geo(self, data: str) -> None:
        """Analisa informações geográficas."""
        try:
            # Formato: geo:latitude,longitude
            coords = data[4:].split(',')  # Remove 'geo:'
            if len(coords) >= 2:
                self.geo_info = {
                    "latitude": float(coords[0]),
                    "longitude": float(coords[1]),
                    "altitude": float(coords[2]) if len(coords) > 2 else None
                }
        except Exception:
            self.geo_info = {"error": "Invalid geo format"}
    
    def _analyze_vcard(self, data: str) -> None:
        """Analisa vCard para extrair informações de contato."""
        try:
            lines = data.split('\n')
            contact_data = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    contact_data[key.upper()] = value
            
            self.contact_info = {
                "name": contact_data.get("FN", ""),
                "organization": contact_data.get("ORG", ""),
                "phone": contact_data.get("TEL", ""),
                "email": contact_data.get("EMAIL", ""),
                "url": contact_data.get("URL", "")
            }
        except Exception:
            self.contact_info = {"error": "Invalid vCard format"}
    
    def _analyze_security(self) -> None:
        """Analisa aspectos de segurança do conteúdo."""
        if not self.qr_data:
            return
        
        security_flags = []
        
        # Verificar URL encurtadoras
        if self.data_type == "url":
            shorteners = [
                "bit.ly", "tinyurl.com", "t.co", "goo.gl", "short.link",
                "ow.ly", "buff.ly", "is.gd", "tiny.cc"
            ]
            
            for shortener in shorteners:
                if shortener in self.qr_data.lower():
                    self.url_shortener_detected = True
                    security_flags.append("url_shortener")
                    break
        
        # Verificar conteúdo suspeito
        suspicious_patterns = [
            r"(?i)(download|install|update).*(exe|apk|dmg)",
            r"(?i)(urgent|immediate|click now|act fast)",
            r"(?i)(free money|earn \$|make money fast)",
            r"(?i)(virus|malware|security alert)"
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, self.qr_data):
                self.suspicious_content = True
                security_flags.append("suspicious_content")
                break
        
        self.security_flags = security_flags if security_flags else None
    
    def set_quality_from_score(self, score: float) -> None:
        """
        Define descrição de qualidade baseada no score.
        
        Args:
            score: Score de qualidade (0-1)
        """
        self.quality_score = score
        
        if score >= 0.9:
            self.quality_description = "excellent"
        elif score >= 0.7:
            self.quality_description = "good"
        elif score >= 0.5:
            self.quality_description = "fair"
        else:
            self.quality_description = "poor"
    
    def get_content_info(self) -> Dict[str, Any]:
        """
        Retorna informações específicas do conteúdo baseado no tipo.
        
        Returns:
            Dicionário com informações específicas do tipo
        """
        if self.data_type == "url" and self.url_info:
            return self.url_info
        elif self.data_type == "wifi" and self.wifi_info:
            return self.wifi_info
        elif self.data_type == "geo" and self.geo_info:
            return self.geo_info
        elif self.data_type == "vcard" and self.contact_info:
            return self.contact_info
        else:
            return {"data": self.qr_data, "type": self.data_type}
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo das informações do QR code.
        
        Returns:
            Dicionário com resumo dos dados
        """
        return {
            "data_type": self.data_type,
            "data_length": self.data_length,
            "qr_properties": {
                "version": self.version,
                "error_correction": self.error_correction_level,
                "mask_pattern": self.mask_pattern,
                "data_utilization": self.data_utilization
            },
            "quality": {
                "score": self.quality_score,
                "description": self.quality_description,
                "confidence": self.read_confidence
            },
            "geometry": {
                "center": [self.center_x, self.center_y] if self.center_x else None,
                "size": [self.width, self.height] if self.width else None,
                "module_size": self.module_size,
                "orientation": self.orientation
            },
            "security": {
                "suspicious_content": self.suspicious_content,
                "url_shortener": self.url_shortener_detected,
                "flags": self.security_flags
            },
            "content_info": self.get_content_info()
        }
    
    def to_dict(self, include_raw_data: bool = True, include_analysis: bool = True) -> Dict[str, Any]:
        """
        Converte para dicionário com opções de inclusão.
        
        Args:
            include_raw_data: Se deve incluir dados brutos
            include_analysis: Se deve incluir análises detalhadas
            
        Returns:
            Dicionário com dados do modelo
        """
        exclude_fields = set()
        
        if not include_raw_data:
            exclude_fields.add("qr_data")
        
        if not include_analysis:
            exclude_fields.update([
                "url_info", "wifi_info", "contact_info", "geo_info",
                "preprocessing_applied", "security_flags"
            ])
        
        return super().to_dict(exclude_fields=exclude_fields)
    
    def __repr__(self) -> str:
        """Representação string do resultado de QR code."""
        return f"<QRCodeResult(job_id={self.job_id}, type={self.data_type}, version={self.version})>"