"""
Catalogue produits & commandes pour Altiaro.
Séparé du server.py pour garder la modularité.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr, Field


class I18nText(BaseModel):
    fr: str = ""
    en: str = ""
    de: str = ""
    nl: str = ""


class ProductCreateInput(BaseModel):
    name: I18nText
    description: Optional[I18nText] = Field(default_factory=I18nText)
    price: float = 0                           # Prix de vente TTC
    cost_price_ht: float = 0                   # Prix d'achat HT (fournisseur)
    vat_rate: Optional[float] = None           # Override ex: 0.20 (sinon taux du site)
    compare_at_price: Optional[float] = None
    currency: str = "EUR"
    images: List[str] = Field(default_factory=list)
    stock: Optional[int] = None                # None = illimité (dropshipping)
    supplier_url: str = ""
    sku: str = ""
    status: str = "active"                     # active | draft | archived
    featured: bool = False
    category: str = ""                          # slug de la collection principale
    tags: List[str] = Field(default_factory=list)  # tags secondaires (matière, couleur, etc.)


class ProductUpdateInput(BaseModel):
    name: Optional[I18nText] = None
    description: Optional[I18nText] = None
    price: Optional[float] = None
    cost_price_ht: Optional[float] = None
    vat_rate: Optional[float] = None
    compare_at_price: Optional[float] = None
    currency: Optional[str] = None
    images: Optional[List[str]] = None
    stock: Optional[int] = None
    supplier_url: Optional[str] = None
    sku: Optional[str] = None
    status: Optional[str] = None
    featured: Optional[bool] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float = Field(ge=0)
    quantity: int = Field(gt=0, le=99)
    currency: str = "EUR"
    image: Optional[str] = None


class ShippingAddress(BaseModel):
    line1: str
    line2: Optional[str] = ""
    city: str
    postal_code: str
    country: str           # Ex: "France"
    country_code: str      # Ex: "FR"


class Customer(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = ""


class OrderCreateInput(BaseModel):
    items: List[OrderItem]
    customer: Customer
    shipping_address: ShippingAddress
    language: str = "fr"
    notes: Optional[str] = ""
