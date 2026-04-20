"""
Catalogue produits & commandes pour Concept Factory.
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
    price: float = 0
    compare_at_price: Optional[float] = None
    currency: str = "EUR"
    images: List[str] = Field(default_factory=list)
    stock: Optional[int] = None  # None = illimité (dropshipping)
    supplier_url: str = ""
    sku: str = ""
    status: str = "active"  # active | draft | archived
    featured: bool = False


class ProductUpdateInput(BaseModel):
    name: Optional[I18nText] = None
    description: Optional[I18nText] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    currency: Optional[str] = None
    images: Optional[List[str]] = None
    stock: Optional[int] = None
    supplier_url: Optional[str] = None
    sku: Optional[str] = None
    status: Optional[str] = None
    featured: Optional[bool] = None


class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
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
