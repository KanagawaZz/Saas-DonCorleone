from django.http import HttpResponse
from django.utils.html import escape
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from apps.orders.models import Order

class ThermalReceiptPrintView(APIView):
    """
    Renders an 80mm / 58mm thermal print page with auto-print triggers.
    Staff only (logged in to the Django admin): the receipt shows customer phone and address.
    Every customer-provided value is HTML-escaped before rendering.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, code):
        order = Order.objects.filter(readable_code__iexact=code.strip()).first()
        if not order:
            try:
                order = Order.objects.filter(id=code.strip()).first()
            except Exception:
                pass

        if not order:
            return HttpResponse("Pedido não encontrado", status=404)

        is_delivery = order.fulfillment_mode == Order.FulfillmentMode.DELIVERY
        date_str = order.created_at.strftime('%d/%m/%Y às %H:%M')

        items_html = ""
        for it in order.items.all():
            flavors_html = ""
            for fl in it.flavors.all():
                flavors_html += f"<div class='item-flavor'>• {escape(fl.proportion)} {escape(fl.flavor_name_snapshot)}</div>"

            crust_html = ""
            if it.crust_name_snapshot and it.crust_name_snapshot != "Sem Borda":
                crust_price_txt = f" (+R$ {it.crust_price_snapshot:.2f})" if it.crust_price_snapshot > 0 else " (Grátis)"
                crust_html = f"<div class='item-crust'>• Borda: {escape(it.crust_name_snapshot)}{crust_price_txt}</div>"

            obs_html = f"<div class='item-obs'>Obs: {escape(it.notes)}</div>" if it.notes else ""

            items_html += f"""
            <div class="comanda-item">
                <div class="item-header">
                    <strong>{it.quantity}x {escape(it.product_name_snapshot)}</strong>
                    <span>R$ {it.subtotal_snapshot:.2f}</span>
                </div>
                {flavors_html}
                {crust_html}
                {obs_html}
            </div>
            """

        troco_info = ""
        if order.payment_method == 'dinheiro' and order.needs_change and order.change_for:
            troco_info = f"<div class='troco-box'>LEVAR TROCO: R$ {order.calculated_change:.2f} (Troco para R$ {order.change_for:.2f})</div>"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <title>Comanda #{escape(order.readable_code)}</title>
            <style>
                @page {{
                    margin: 0;
                    size: 80mm auto;
                }}
                body {{
                    font-family: 'Courier New', monospace, sans-serif;
                    width: 78mm;
                    margin: 0 auto;
                    padding: 8px 4px;
                    color: #000;
                    background: #fff;
                    font-size: 13px;
                    line-height: 1.3;
                }}
                .text-center {{ text-align: center; }}
                .text-right {{ text-align: right; }}
                .bold {{ font-weight: bold; }}
                .divider {{ border-top: 1px dashed #000; margin: 6px 0; }}
                .header-title {{ font-size: 16px; font-weight: bold; text-align: center; margin-bottom: 2px; }}
                .order-code {{ font-size: 20px; font-weight: 900; text-align: center; margin: 4px 0; }}
                .badge-mode {{ display: inline-block; padding: 2px 6px; font-size: 14px; font-weight: bold; border: 1px solid #000; margin-top: 2px; }}
                .comanda-item {{ margin-bottom: 6px; }}
                .item-header {{ display: flex; justify-content: space-between; font-weight: bold; }}
                .item-flavor, .item-crust {{ font-size: 12px; padding-left: 8px; }}
                .item-obs {{ font-size: 11px; font-style: italic; padding-left: 8px; font-weight: bold; }}
                .totals-row {{ display: flex; justify-content: space-between; font-size: 13px; }}
                .grand-total {{ display: flex; justify-content: space-between; font-size: 16px; font-weight: bold; margin-top: 4px; }}
                .troco-box {{ font-weight: bold; background: #eee; padding: 4px; text-align: center; margin-top: 4px; border: 1px solid #000; }}
                @media print {{
                    .no-print {{ display: none; }}
                }}
                .btn-print {{ background: #000; color: #fff; padding: 8px 16px; font-weight: bold; border: none; cursor: pointer; border-radius: 4px; margin-bottom: 10px; width: 100%; }}
            </style>
        </head>
        <body>
            <button class="btn-print no-print" onclick="window.print()">IMPRIMIR COMANDA (80mm)</button>
            <div class="header-title">DON CORLEONE</div>
            <div class="text-center">Cantina &amp; Pizzaria · Cidade Alta</div>
            <div class="text-center">{date_str}</div>
            <div class="divider"></div>
            
            <div class="order-code">#{escape(order.readable_code)}</div>
            <div class="text-center">
                <span class="badge-mode">{'DELIVERY 🛵' if is_delivery else 'RETIRADA NO BALCÃO 🏪'}</span>
            </div>
            
            <div class="divider"></div>
            <div><strong>Cliente:</strong> {escape(order.customer_name)}</div>
            <div><strong>WhatsApp:</strong> {escape(order.customer_phone)}</div>
            {f'''
            <div class="divider"></div>
            <div><strong>ENDEREÇO DE ENTREGA:</strong></div>
            <div>{escape(order.delivery_street)}, {escape(order.delivery_number)}</div>
            {f'<div>Compl.: {escape(order.delivery_complement)}</div>' if order.delivery_complement else ''}
            <div>Bairro: <strong>{escape(order.delivery_neighborhood)}</strong> - {escape(order.delivery_city)}</div>
            {f'<div>Ref: {escape(order.delivery_reference)}</div>' if order.delivery_reference else ''}
            ''' if is_delivery else ''}
            
            <div class="divider"></div>
            <div class="bold text-center">ITENS DO PEDIDO</div>
            <div class="divider"></div>
            {items_html}
            
            <div class="divider"></div>
            <div class="totals-row">
                <span>Subtotal:</span>
                <span>R$ {order.subtotal:.2f}</span>
            </div>
            {f'''
            <div class="totals-row">
                <span>Desconto ({escape(order.coupon_applied)}):</span>
                <span>- R$ {order.discount_amount:.2f}</span>
            </div>
            ''' if order.discount_amount > 0 else ''}
            {f'''
            <div class="totals-row">
                <span>Taxa de Entrega:</span>
                <span>R$ {order.delivery_fee:.2f}</span>
            </div>
            ''' if is_delivery else ''}
            <div class="grand-total">
                <span>TOTAL:</span>
                <span>R$ {order.total_amount:.2f}</span>
            </div>
            
            <div class="divider"></div>
            <div><strong>Pagamento:</strong> {order.get_payment_method_display()}</div>
            {troco_info}
            {f'<div style="margin-top:4px;"><strong>Obs:</strong> {escape(order.notes)}</div>' if order.notes else ''}
            
            <div class="divider"></div>
            <div class="text-center bold" style="font-size:11px;">Don Corleone Pizzaria · (65) 99265-0139</div>
            <div class="text-center" style="font-size:10px; margin-top: 4px;">.</div>
            
            <script>
                // Auto trigger print if parameter ?autoprint=1 is provided
                if (window.location.search.includes('autoprint=1')) {{
                    window.onload = function() {{
                        window.print();
                    }}
                }}
            </script>
        </body>
        </html>
        """
        return HttpResponse(html_content, content_type="text/html; charset=utf-8")
