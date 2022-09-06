# -*- coding: utf-8 -*-

from sqlite3 import PARSE_DECLTYPES
from odoo import _, api, exceptions, fields, models
import random


class ProductTemplate(models.Model):
    _inherit = "product.template"

    codigo_interno = fields.Char()
    codigo_compania_id = fields.Many2one('codigo.compania')
    create_date_anno = fields.Char()
    cod_articulo = fields.Char(related='id')
    temporada = fields.Selection([
        ('w', 'Invierno'),
        ('s', 'Primavera'),
        ('u', 'Verano'),
        ('o', 'Otonno'),
        ('su', 'Crucero Primavera/Verano'),
        ('fw', 'Crucero Otonno/Invierno')], string='Temporada',
        copy=False, default='c')

    @api.onchange("codigo_compania_id")
    def _trae_anno(self):
        for r in self:
            v1 = 00
            if r.create_date:
                v1 = r.create_date
                r.create_date_anno = int(22)

    @api.onchange("default_code")
    def _trae_refe(self):
        for r in self:
            if r.default_code:
                r.barcode = r.default_code

class ProductProduct(models.Model):
    _inherit = "product.product"

    codigo_interno = fields.Char()


class CodigoCompania(models.Model):
    _name = "codigo.compania"

    name = fields.Char()
    codigo = fields.Char()

class ProductCategory(models.Model):
    _inherit = "product.category"

    padre = fields.Char()
    hijo = fields.Char()
    nieto = fields.Char()

    @api.onchange('name')
    def get_code(self):
        for i in self:
            i.padre = int(random.uniform(1, 99))
    
    @api.onchange('name')
    def get_code_hijo(self):
        for i in self:
            i.hijo = int(random.uniform(1, 99))

    @api.onchange('name')
    def get_code_nieto(self):
        for i in self:
            i.nieto = int(random.uniform(1, 999))
             



