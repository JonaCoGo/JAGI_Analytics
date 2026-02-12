# app/reports/excel_exporter.py

import pandas as pd
from datetime import datetime

from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

# ======================================================
# 🔧 EXPORTADOR EXCEL FORMATEADO
# ======================================================

def exportar_excel_formateado(df, archivo, nombre_reporte="Reporte", tipo_formato="general"):
    """
    Crea un Excel con una hoja por tienda, con formato visual profesional.
    
    Args:
        df: DataFrame con los datos a exportar
        archivo: Nombre del archivo de salida
        nombre_reporte: Título del reporte
        tipo_formato: Tipo de formato a aplicar
            - "general": Formato estándar (default)
            - "picking": Formato para picking con header de control
            - "auditoria": Formato para auditoría (futuro)
    """

    if df.empty:
        raise ValueError("El DataFrame está vacío, no se puede exportar.")

    # 🔍 Detectar columna de tienda según el tipo de reporte
    if "tienda" in df.columns:
        col_tienda = "tienda"
    elif "tienda_origen" in df.columns:
        col_tienda = "tienda_origen"
    elif "tienda_destino" in df.columns:
        col_tienda = "tienda_destino"
    else:
        raise KeyError(
            f"No se encontró ninguna columna de tienda en el DataFrame.\n"
            f"Columnas disponibles: {list(df.columns)}"
        )

    # --- Preparar datos según tipo de formato ---
    df_procesado = df.copy()
    
    if tipo_formato == "picking":
        # Para picking: renombrar columnas y preparar estructura
        column_mapping = {
            'c_barra': 'Cod.Barras',
            'd_marca': 'Marca',
            'color': 'Color',
            'cantidad_a_despachar': 'Cantidad',
            'observacion': 'Observacion'
        }
        
        # Filtrar solo las columnas que existen y renombrarlas
        columnas_picking = [col for col in column_mapping.keys() if col in df_procesado.columns]
        df_procesado = df_procesado[[col_tienda] + columnas_picking].copy()
        df_procesado = df_procesado.rename(columns=column_mapping)

    # --- Crear archivo base ---
    with pd.ExcelWriter(archivo, engine="openpyxl") as writer:
        for tienda, df_tienda in df_procesado.groupby(col_tienda, sort=True):
            hoja = str(tienda)[:25] if isinstance(tienda, str) else str(tienda)
            
            # Para picking: quitar la columna de tienda antes de escribir
            if tipo_formato == "picking":
                df_escribir = df_tienda.drop(columns=[col_tienda])
            else:
                df_escribir = df_tienda
            
            df_escribir.to_excel(writer, sheet_name=hoja, index=False)

    # --- Aplicar formato con openpyxl ---
    wb = load_workbook(archivo)
    thin = Side(border_style="thin", color="000000")
    medium = Side(border_style="medium", color="000000")

    # 🎨 Colores de estilo
    header_fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF", fill_type="solid")
    alt_fill = PatternFill(start_color="F9F9F9", end_color="F9F9F9", fill_type="solid")
    control_fill = PatternFill(start_color="E8F4F8", end_color="E8F4F8", fill_type="solid")

    for ws in wb.worksheets:
        nombre_tienda = ws.title
        
        # --- Aplicar formato según tipo ---
        if tipo_formato == "picking":
            _aplicar_formato_picking(ws, nombre_tienda, nombre_reporte, thin, medium, header_fill, alt_fill, control_fill)
        else:
            _aplicar_formato_general(ws, nombre_reporte, thin, header_fill, alt_fill)

    wb.save(archivo)
    print(f"\n🖨️ Archivo listo y formateado: {archivo}")


def _aplicar_formato_picking(ws, nombre_tienda, nombre_reporte, thin, medium, header_fill, alt_fill, control_fill):
    """Aplica formato específico para picking con header de control."""
    
    # 1. INSERTAR FILAS PARA HEADER DE CONTROL (10 filas)
    ws.insert_rows(1, 10)
    
    # 2. AGREGAR HEADER DE CONTROL
    _agregar_header_picking(ws, nombre_tienda, nombre_reporte, control_fill, thin, medium)
    
    # 3. AGREGAR COLUMNA DE CHECKBOX AL INICIO
    ws.insert_cols(1)
    ws.cell(row=11, column=1).value = "☐"  # Header de checkbox
    ws.column_dimensions['A'].width = 4
    
    # 4. FORMATEAR HEADERS DE DATOS (ahora en fila 11)
    fila_header = 11
    ws.row_dimensions[fila_header].height = 30
    
    for cell in ws[fila_header]:
        cell.font = Font(bold=True, size=11, color="000000")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=medium, left=thin, right=thin, bottom=medium)
        cell.fill = header_fill
    
    # 5. AUTO-AJUSTE DE COLUMNAS (mejorado)
    for col_idx in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col_idx)
        
        if col_idx == 1:  # Columna checkbox
            ws.column_dimensions[col_letter].width = 4
            continue
        
        # Calcular ancho óptimo basado en contenido
        max_length = 0
        for cell in ws[col_letter]:
            if cell.value and cell.row >= fila_header:  # Solo desde headers hacia abajo
                cell_length = len(str(cell.value))
                max_length = max(max_length, cell_length)
        
        # Ajustar ancho con límites razonables
        calculated_width = min(max(max_length + 2, 10), 50)
        ws.column_dimensions[col_letter].width = calculated_width
    
    # 6. AGREGAR CHECKBOXES Y FORMATEAR FILAS DE DATOS
    for i in range(fila_header + 1, ws.max_row + 1):
        # Agregar checkbox en columna A
        ws.cell(row=i, column=1).value = "☐"
        ws.cell(row=i, column=1).alignment = Alignment(horizontal="center", vertical="center")
        
        # Alternar color de fondo
        fill = alt_fill if (i - fila_header) % 2 == 0 else None
        
        # Aplicar bordes y formato a toda la fila
        for cell in ws[i]:
            cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            if fill and cell.column > 1:  # No aplicar fill a checkbox
                cell.fill = fill
    
    # 7. CONFIGURACIÓN DE IMPRESIÓN (VERTICAL)
    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = 0.5
    ws.page_margins.right = 0.5
    ws.page_margins.top = 0.75
    ws.page_margins.bottom = 0.75
    
    # 8. CONGELAR PANELES
    ws.freeze_panes = f"A{fila_header + 1}"
    
    # 9. ENCABEZADO Y PIE DE PÁGINA
    try:
        ws.oddHeader.left.text = f"&L{nombre_reporte}"
        ws.oddHeader.right.text = f"&R{nombre_tienda}"
        ws.oddFooter.center.text = "&CPágina &P de &N"
    except AttributeError:
        pass


def _agregar_header_picking(ws, nombre_tienda, nombre_reporte, control_fill, thin, medium):
    """Crea el header de control para formato picking."""
    
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    
    # FILA 1-2: TÍTULO
    ws.merge_cells('A1:F2')
    titulo_cell = ws['A1']
    titulo_cell.value = f"JAGI - {nombre_reporte.upper()}"
    titulo_cell.font = Font(bold=True, size=16, color="1F4E78")
    titulo_cell.alignment = Alignment(horizontal="center", vertical="center")
    titulo_cell.fill = control_fill
    titulo_cell.border = Border(
        top=medium, left=medium, right=medium, bottom=thin,
        outline=True
    )
    
    # FILA 3: TIENDA Y FECHA
    ws.merge_cells('A3:C3')
    tienda_cell = ws['A3']
    tienda_cell.value = f"TIENDA: {nombre_tienda}"
    tienda_cell.font = Font(bold=True, size=12)
    tienda_cell.alignment = Alignment(horizontal="left", vertical="center")
    tienda_cell.fill = control_fill
    
    ws.merge_cells('D3:F3')
    fecha_cell = ws['D3']
    fecha_cell.value = f"Fecha: {fecha_actual}"
    fecha_cell.font = Font(size=11)
    fecha_cell.alignment = Alignment(horizontal="right", vertical="center")
    fecha_cell.fill = control_fill
    
    # FILA 4: SEPARADOR
    ws.merge_cells('A4:F4')
    sep_cell = ws['A4']
    sep_cell.value = "CONTROL DE PICKING"
    sep_cell.font = Font(bold=True, size=11, color="FFFFFF")
    sep_cell.alignment = Alignment(horizontal="center", vertical="center")
    sep_cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    
    # FILA 5-6: HORA INICIO Y FINAL
    ws['A5'] = "Hora Inicio:"
    ws['A5'].font = Font(bold=True, size=10)
    ws.merge_cells('B5:C5')
    ws['B5'] = "____________________"
    
    ws['D5'] = "Hora Final:"
    ws['D5'].font = Font(bold=True, size=10)
    ws.merge_cells('E5:F5')
    ws['E5'] = "____________________"
    
    # FILA 7: ENCARGADO
    ws['A7'] = "Encargado:"
    ws['A7'].font = Font(bold=True, size=10)
    ws.merge_cells('B7:F7')
    ws['B7'] = "_________________________________________________________"
    
    # FILA 8-9: FIRMA
    ws['A9'] = "Firma:"
    ws['A9'].font = Font(bold=True, size=10)
    ws.merge_cells('B9:D9')
    ws['B9'] = "________________________________"
    
    ws['E9'] = "Fecha:"
    ws['E9'].font = Font(bold=True, size=10)
    ws['F9'] = "___/___/______"
    
    # Aplicar bordes y fill a sección de control
    for row in range(3, 10):
        for col in range(1, 7):
            cell = ws.cell(row=row, column=col)
            cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
            if row >= 5:  # Solo las filas de datos del control
                cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    
    # Borde exterior grueso
    for col in range(1, 7):
        ws.cell(row=3, column=col).border = Border(
            top=medium if col == 1 else thin,
            left=medium if col == 1 else thin,
            right=medium if col == 6 else thin,
            bottom=thin
        )
        ws.cell(row=9, column=col).border = Border(
            top=thin,
            left=medium if col == 1 else thin,
            right=medium if col == 6 else thin,
            bottom=medium
        )
    
    # FILA 10: ESPACIO EN BLANCO
    ws.row_dimensions[10].height = 5


def _aplicar_formato_general(ws, nombre_reporte, thin, header_fill, alt_fill):
    """Aplica formato estándar general."""
    
    # HEADERS
    ws.row_dimensions[1].height = 40
    for cell in ws[1]:
        cell.font = Font(bold=True, size=11, color="000000")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        cell.fill = header_fill

    # AUTO-AJUSTE DE COLUMNAS (mejorado)
    for col_idx in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col_idx)
        
        max_length = 0
        for cell in ws[col_letter]:
            if cell.value:
                cell_length = len(str(cell.value))
                max_length = max(max_length, cell_length)
        
        # Ajustar ancho con límites razonables
        calculated_width = min(max(max_length + 2, 10), 50)
        ws.column_dimensions[col_letter].width = calculated_width

    # BORDES Y ALTERNANCIA DE COLOR EN FILAS
    for i, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column), start=2):
        fill = alt_fill if i % 2 == 0 else None
        for cell in row:
            cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            if fill:
                cell.fill = fill

    ws.freeze_panes = "A2"

    # CONFIGURACIÓN DE IMPRESIÓN (VERTICAL)
    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = 0.5
    ws.page_margins.right = 0.5
    ws.page_margins.top = 0.75
    ws.page_margins.bottom = 0.75

    # ENCABEZADO Y PIE
    try:
        ws.oddHeader.left.text = f"&LJAGI - {nombre_reporte}"
        ws.oddHeader.right.text = "&RPágina &P de &N"
        ws.oddFooter.center.text = "&CGenerado automáticamente"
    except AttributeError:
        pass