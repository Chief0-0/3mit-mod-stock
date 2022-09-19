# -*- coding: utf-8 -*-

from email.policy import default
from sqlite3 import PARSE_DECLTYPES
from string import digits
import string
from odoo import _, api, exceptions, fields, models
import random
from odoo.osv import expression
import logging
import re


class ProductTemplate(models.Model):
    _inherit = "product.template"

    codigo_interno = fields.Char(size=16)
    padre = fields.Char(string="Codigo Interno")
    hijo = fields.Char()
    nieto = fields.Char()
    cod_marca = fields.Char()
    cod_art = fields.Char()

    codigo_compania_id = fields.Many2one('codigo.compania')
    create_date_anno = fields.Char()
    cod_articulo = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('increment_your_field'))
    temporada = fields.Selection([
        ('w', 'Invierno'),
        ('s', 'Primavera'),
        ('u', 'Verano'),
        ('o', 'Otonno'),
        ('su', 'Crucero Primavera/Verano'),
        ('fw', 'Crucero Otonno/Invierno')], string='Temporada',
        copy=False, default='o')

    invierno = fields.Boolean()
    primavera = fields.Boolean()
    verano = fields.Boolean()
    otonno = fields.Boolean()
    crucero_primavera_verano = fields.Boolean()
    crucero_otonno_invierno = fields.Boolean()

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

    def generar_cod(self):
        for r in self:
            if r.cod_art:
                r.codigo_interno = '%s%s%s%s%s' % (r.padre,r.hijo,r.nieto,r.cod_marca,r.cod_art)

class ProductProduct(models.Model): 
    _inherit = "product.product"

    padre = fields.Char(string="Codigo Interno")
    hijo = fields.Char()
    nieto = fields.Char()
    cod_marca = fields.Char()
    cod_art = fields.Char()

    temporada = fields.Selection([
        ('w', 'Invierno'),
        ('s', 'Primavera'),
        ('u', 'Verano'),
        ('o', 'Otonno'),
        ('su', 'Crucero Primavera/Verano'),
        ('fw', 'Crucero Otonno/Invierno')], string='Temporada',
        copy=False, default='o')

    invierno = fields.Boolean()
    primavera = fields.Boolean()
    verano = fields.Boolean()
    otonno = fields.Boolean()
    crucero_primavera_verano = fields.Boolean()
    crucero_otonno_invierno = fields.Boolean()

    def generar_cod(self):
        for r in self:
            padre = r.categ_id.padre
            hijo = r.categ_id.hijo
            nieto = r.categ_id.nieto
            cod_marca = r.product_brand_id.cod
            cor_art = r.cod_art
            if r.cod_art:
                r.codigo_interno = '%s%s%s%s%s' % (padre,hijo,nieto,cod_marca,cor_art)
            #return (d['id'], name)

   # @api.onchange("name")
    #def auto_codigo_interno():
     #   codigo = 1
      #  for r in self:
       #     r.codigo_interno = 000 + r.id


    def name_get(self):
        # TDE: this could be cleaned a bit I think

        def _name_get(d):
            name = d.get('name', '')
            code = self._context.get('display_default_code', True) and d.get('default_code', False) or False
            code_i = d.get('codigo_interno', '')
            if code:
                name = '[%s] %s %s' % (code,code_i,name)
            return (d['id'], name)

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []

        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        # Use `load=False` to not call `name_get` for the `product_tmpl_id`
        self.sudo().read(['name', 'default_code', 'codigo_interno','product_tmpl_id'], load=False)

        product_template_ids = self.sudo().mapped('product_tmpl_id').ids

        if partner_ids:
            supplier_info = self.env['product.supplierinfo'].sudo().search([
                ('product_tmpl_id', 'in', product_template_ids),
                ('name', 'in', partner_ids),
            ])
            # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
            # Use `load=False` to not call `name_get` for the `product_tmpl_id` and `product_id`
            supplier_info.sudo().read(['product_tmpl_id', 'product_id', 'product_name', 'product_code'], load=False)
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)
        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = self.env['product.supplierinfo'].sudo().browse(self.env.context.get('seller_id')) or []
            if not sellers and partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or product.default_code,
                              'codigo_interno': product.codigo_interno,
                              }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'default_code': product.default_code,
                          'codigo_interno': product.codigo_interno,
                          }
                result.append(_name_get(mydict))
        return result


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            product_ids = []
            if operator in positive_operators:
                product_ids = list(self._search([('codigo_interno', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid))
                if not product_ids:
                    product_ids = list(self._search([('barcode', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid))
            if not product_ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                product_ids = list(self._search(args + [('codigo_interno', operator, name)], limit=limit))
                if not limit or len(product_ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(product_ids)) if limit else False
                    product2_ids = self._search(args + [('name', operator, name), ('id', 'not in', product_ids)], limit=limit2, access_rights_uid=name_get_uid)
                    product_ids.extend(product2_ids)
            elif not product_ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = expression.OR([
                    ['&', ('codigo_interno', operator, name), ('name', operator, name)],
                    ['&', ('codigo_interno', '=', False), ('name', operator, name)],
                ])
                domain = expression.AND([args, domain])
                product_ids = list(self._search(domain, limit=limit, access_rights_uid=name_get_uid))
            if not product_ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    product_ids = list(self._search([('codigo_interno', '=', res.group(2))] + args, limit=limit, access_rights_uid=name_get_uid))
            # still no results, partner in context: search on supplier info as last hope to find something
            if not product_ids and self._context.get('partner_id'):
                suppliers_ids = self.env['product.supplierinfo']._search([
                    ('name', '=', self._context.get('partner_id')),
                    '|',
                    ('product_code', operator, name),
                    ('product_name', operator, name)], access_rights_uid=name_get_uid)
                if suppliers_ids:
                    product_ids = self._search([('product_tmpl_id.seller_ids', 'in', suppliers_ids)], limit=limit, access_rights_uid=name_get_uid)
        else:
            product_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return product_ids
        

class CodigoCompania(models.Model):
    _name = "codigo.compania"

    name = fields.Char()
    codigo = fields.Char()

class ProductCategory(models.Model):
    _inherit = "product.category"

    padre = fields.Char()
    hijo = fields.Char()
    nieto = fields.Char()
    t_nivel = fields.Boolean()

    @api.onchange('name')
    def get_code(self):
        for i in self:
            i.padre = int(random.uniform(1, 99))
    
    @api.onchange('parent_id')
    def get_code_hijo(self):
        for i in self:
            if not i.t_nivel:
                i.hijo = int(random.uniform(1, 99))

    @api.onchange('parent_id')
    def get_code_nieto(self):
        for i in self:
            i.nieto = int(random.uniform(1, 999))
             
class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    #effective_date = fields.Char()
    temporada = fields.Selection([
        ('w', 'Invierno'),
        ('s', 'Primavera'),
        ('u', 'Verano'),
        ('o', 'Otonno'),
        ('su', 'Crucero Primavera/Verano'),
        ('fw', 'Crucero Otonno/Invierno')])
    
    invierno = fields.Boolean()
    primavera = fields.Boolean()
    verano = fields.Boolean()
    otonno = fields.Boolean()
    crucero_primavera_verano = fields.Boolean()
    crucero_otonno_invierno = fields.Boolean()
    

class SaleReport(models.Model):
    _inherit = "sale.report"

    temporada = fields.Selection([
        ('w', 'Invierno'),
        ('s', 'Primavera'),
        ('u', 'Verano'),
        ('o', 'Otonno'),
        ('su', 'Crucero Primavera/Verano'),
        ('fw', 'Crucero Otonno/Invierno')])

    invierno = fields.Boolean()
    primavera = fields.Boolean()
    verano = fields.Boolean()
    otonno = fields.Boolean()
    crucero_primavera_verano = fields.Boolean()
    crucero_otonno_invierno = fields.Boolean()


class InvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    temporada = fields.Selection([
        ('w', 'Invierno'),
        ('s', 'Primavera'),
        ('u', 'Verano'),
        ('o', 'Otonno'),
        ('su', 'Crucero Primavera/Verano'),
        ('fw', 'Crucero Otonno/Invierno')])
    
    invierno = fields.Boolean()
    primavera = fields.Boolean()
    verano = fields.Boolean()
    otonno = fields.Boolean()
    crucero_primavera_verano = fields.Boolean()
    crucero_otonno_invierno = fields.Boolean()


    _depends = {
        'account.move': [
            'name', 'state', 'move_type', 'partner_id', 'invoice_user_id', 'fiscal_position_id',
            'invoice_date', 'invoice_date_due', 'invoice_payment_term_id', 'partner_bank_id',
        ],
        'account.move.line': [
            'quantity', 'price_subtotal', 'amount_residual', 'balance', 'amount_currency',
            'move_id', 'product_id', 'product_uom_id', 'account_id', 'analytic_account_id',
            'journal_id', 'company_id', 'currency_id', 'partner_id',
        ],
        'product.product': ['product_tmpl_id', 'temporada', 'invierno', 'primavera', 'verano', 'otonno', 'crucero_primavera_verano', 'crucero_otonno_invierno'],
        'product.template': ['categ_id', 'temporada', 'invierno', 'primavera', 'verano', 'otonno', 'crucero_primavera_verano', 'crucero_otonno_invierno'],
        'uom.uom': ['category_id', 'factor', 'name', 'uom_type'],
        'res.currency.rate': ['currency_id', 'name'],
        'res.partner': ['country_id'],
    }

    @property
    def _table_query(self):
        return '%s %s %s' % (self._select(), self._from(), self._where())

    @api.model
    def _select(self):
        return '''
            SELECT
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.company_currency_id,
                line.partner_id AS commercial_partner_id,
                move.state,
                move.move_type,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.payment_state,
                move.invoice_date,
                move.invoice_date_due,
                uom_template.id                                             AS product_uom_id,
                template.categ_id                                           AS product_categ_id,
                template.temporada                                          AS temporada,
                template.invierno                                           AS invierno,
                template.primavera                                          AS primavera,
                template.verano                                             AS verano,
                template.otonno                                             AS otonno,
                template.crucero_primavera_verano                           AS crucero_primavera_verano,
                template.crucero_otonno_invierno                            AS crucero_otonno_invierno,
                line.quantity / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS quantity,
                -line.balance * currency_table.rate                         AS price_subtotal,
                -COALESCE(
                   -- Average line price
                   (line.balance / NULLIF(line.quantity, 0.0)) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                   -- convert to template uom
                   * (NULLIF(COALESCE(uom_line.factor, 1), 0.0) / NULLIF(COALESCE(uom_template.factor, 1), 0.0)),
                   0.0) * currency_table.rate                               AS price_average,
                COALESCE(partner.country_id, commercial_partner.country_id) AS country_id
        '''

class TPVReport(models.Model):
    _inherit = "report.pos.order"

    temporada = fields.Selection([
        ('w', 'Invierno'),
        ('s', 'Primavera'),
        ('u', 'Verano'),
        ('o', 'Otonno'),
        ('su', 'Crucero Primavera/Verano'),
        ('fw', 'Crucero Otonno/Invierno')])

    invierno = fields.Boolean()
    primavera = fields.Boolean()
    verano = fields.Boolean()
    otonno = fields.Boolean()
    crucero_primavera_verano = fields.Boolean()
    crucero_otonno_invierno = fields.Boolean()

    def _select(self):
        return """
            SELECT
                MIN(l.id) AS id,
                COUNT(*) AS nbr_lines,
                s.date_order AS date,
                SUM(l.qty) AS product_qty,
                SUM(l.qty * l.price_unit / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS price_sub_total,
                SUM(ROUND((l.qty * l.price_unit) * (100 - l.discount) / 100 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END, cu.decimal_places)) AS price_total,
                SUM((l.qty * l.price_unit) * (l.discount / 100) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS total_discount,
                CASE
                    WHEN SUM(l.qty * u.factor) = 0 THEN NULL
                    ELSE (SUM(l.qty*l.price_unit / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END)/SUM(l.qty * u.factor))::decimal
                END AS average_price,
                SUM(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)) AS delay_validation,
                s.id as order_id,
                s.partner_id AS partner_id,
                s.state AS state,
                s.user_id AS user_id,
                s.company_id AS company_id,
                s.sale_journal AS journal_id,
                l.product_id AS product_id,
                pt.categ_id AS product_categ_id,
                p.product_tmpl_id,
                p.temporada AS temporada,
                p.invierno AS invierno,
                p.primavera AS primavera,
                p.verano AS verano,
                p.otonno AS otonno,
                p.crucero_primavera_verano AS crucero_primavera_verano,
                p.crucero_otonno_invierno AS crucero_otonno_invierno,
                ps.config_id,
                pt.pos_categ_id,
                s.pricelist_id,
                s.session_id,
                s.account_move IS NOT NULL AS invoiced
        """

    def _group_by(self):
        return """
            GROUP BY
                s.id, s.date_order, s.partner_id,s.state, pt.categ_id,
                s.user_id, s.company_id, s.sale_journal,
                s.pricelist_id, s.account_move, s.create_date, s.session_id,
                l.product_id,
                pt.categ_id, pt.pos_categ_id,
                p.product_tmpl_id,
                p.temporada,
                p.invierno,
                p.Primavera,
                p.Verano,
                p.Otonno,
                p.Crucero_Primavera_Verano,
                p.Crucero_Otonno_Invierno,
                ps.config_id
        """

class ProductBrand(models.Model):
    _inherit = 'as.product.brand'

    cod = fields.Char()
