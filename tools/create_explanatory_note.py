from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "Пояснительная_записка_CRM_Z1.docx"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=130, bottom=100, end=130) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color="D9D9D9", size="6") -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def remove_paragraph_border(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_borders = p_pr.find(qn("w:pBdr"))
    if p_borders is not None:
        p_pr.remove(p_borders)
    p_borders = OxmlElement("w:pBdr")
    for edge in ("top", "left", "bottom", "right", "between", "bar"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "nil")
        p_borders.append(border)
    p_pr.append(p_borders)


def set_font(run, name="Times New Roman", size=12, bold=None, color="000000") -> None:
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold


def add_body(doc, text: str, *, bold_lead: str | None = None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Inches(0.35)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.keep_together = True
    if bold_lead and text.startswith(bold_lead):
        lead = p.add_run(bold_lead)
        set_font(lead, bold=True)
        tail = p.add_run(text[len(bold_lead):])
        set_font(tail)
    else:
        run = p.add_run(text)
        set_font(run)
    return p


def add_bullet(doc, text: str):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.35)
    p.paragraph_format.first_line_indent = Inches(-0.2)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.1
    set_font(p.add_run(text))
    return p


def add_numbered(doc, number: int, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.35)
    p.paragraph_format.first_line_indent = Inches(-0.2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_together = True
    set_font(p.add_run(f"{number}. "))
    set_font(p.add_run(text))
    return p


def add_heading(doc, text: str, level: int = 1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(12 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(5)
    run = p.add_run(text)
    set_font(run, size=15 if level == 1 else 13, bold=True)
    return p


def add_table(doc, headers, rows, widths, *, compact=False):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    header = table.rows[0]
    set_repeat_table_header(header)
    prevent_row_split(header)
    for i, text in enumerate(headers):
        cell = header.cells[i]
        cell.width = Inches(widths[i])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cell, "1F4E78")
        set_cell_margins(cell, top=60 if compact else 100, bottom=60 if compact else 100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_font(p.add_run(text), size=9.5 if compact else 10, bold=True, color="FFFFFF")
    for row_index, values in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        if row_index % 2:
            for cell in row.cells:
                set_cell_shading(cell, "F3F7FA")
        for i, value in enumerate(values):
            cell = row.cells[i]
            cell.width = Inches(widths[i])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell, top=60 if compact else 100, bottom=60 if compact else 100)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0 if compact else 1.05
            set_font(p.add_run(str(value)), size=9 if compact else 9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def configure_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.font.size = Pt(12)
    for style_name in ("Title", "Heading 1", "Heading 2"):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.color.rgb = RGBColor(0, 0, 0)
        p_pr = style._element.get_or_add_pPr()
        p_borders = p_pr.find(qn("w:pBdr"))
        if p_borders is not None:
            p_pr.remove(p_borders)
    doc.styles["Title"].font.size = Pt(22)
    doc.styles["Heading 1"].font.size = Pt(15)
    doc.styles["Heading 2"].font.size = Pt(13)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    set_font(run, size=9)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend((fld_char1, instr_text, fld_char2))


def build_document() -> None:
    doc = Document()
    configure_styles(doc)
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.85)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.95)
    section.right_margin = Inches(0.75)
    section.header_distance = Inches(0.3)
    section.footer_distance = Inches(0.35)
    section.different_first_page_header_footer = True

    for _ in range(4):
        doc.add_paragraph()
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(18)
    remove_paragraph_border(title)
    set_font(title.add_run("Пояснительная записка"), size=22, bold=True)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(10)
    set_font(subtitle.add_run("к учебному проекту CRM Z1"), size=16, bold=True)
    project = doc.add_paragraph()
    project.alignment = WD_ALIGN_PARAGRAPH.CENTER
    project.paragraph_format.space_after = Pt(8)
    set_font(project.add_run("Конфигурация CRM продажи маркетинг и сервис"), size=14)
    platform = doc.add_paragraph()
    platform.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(platform.add_run("Платформа 1С Предприятие 8.3 учебная версия"), size=12)
    for _ in range(6):
        doc.add_paragraph()
    year = doc.add_paragraph()
    year.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(year.add_run("2026"), size=12)

    doc.add_page_break()

    add_heading(doc, "1 Назначение и область применения")
    add_body(
        doc,
        "Разработанная конфигурация предназначена для ведения клиентской базы, хранения контактных лиц, регистрации взаимодействий и контроля последующих действий. Решение объединяет задачи продаж, маркетинга и сервиса в одной файловой информационной базе 1С.",
    )
    add_body(
        doc,
        "Основной результат проекта - работающая учебная CRM, в которой пользователь может зарегистрировать клиента и его контакты, создать взаимодействие, связать завершенное действие с будущим, получить напоминание и сформировать отчет по активности клиентов.",
    )

    add_heading(doc, "2 Структура конфигурации")
    add_body(doc, "Командный интерфейс разделен на три функциональных раздела:")
    add_bullet(doc, "Продажи - клиенты, контактные лица, взаимодействия, планирование и отчет по активности.")
    add_bullet(doc, "Маркетинг - те же клиентские данные, взаимодействия и отчет для анализа коммуникаций.")
    add_bullet(doc, "Сервис - клиенты, контактные лица, взаимодействия и команда планирования.")

    add_table(
        doc,
        ["Объект", "Назначение", "Основные данные"],
        [
            ("Справочник Клиенты", "Хранение организаций и заказчиков", "Наименование, источник, телефон, e-mail, комментарий, дополнительные телефоны и адреса"),
            ("Справочник Контактные лица", "Хранение представителей клиента", "ФИО, клиент-владелец, телефон, e-mail, роль, основной контакт, комментарий"),
            ("Документ Взаимодействие", "Регистрация коммуникаций", "Дата, клиент, контакт, вид, содержание, результат, следующее действие, напоминание"),
            ("Отчет Активности клиентов", "Просмотр истории действий", "Клиент, дата, вид, содержание и результат"),
        ],
        [1.55, 1.75, 3.5],
    )

    add_heading(doc, "3 Модель данных")
    add_heading(doc, "3.1 Клиенты", level=2)
    add_body(
        doc,
        "Карточка клиента содержит наименование, основной телефон, основной электронный адрес, источник появления и многострочный комментарий. Источник выбирается из перечисления: реклама, рекомендация, сайт, выставка или другое. Для хранения нескольких телефонов и электронных адресов используются отдельные табличные части.",
    )
    add_heading(doc, "3.2 Контактные лица", level=2)
    add_body(
        doc,
        "Контактное лицо подчинено конкретному клиенту. Для него сохраняются ФИО, телефон, электронная почта, роль, признак основного контакта и комментарий. Роль выбирается из перечисления, включающего лицо, принимающее решение, закупщика, технического специалиста и другое.",
    )
    add_heading(doc, "3.3 Взаимодействия", level=2)
    add_body(
        doc,
        "Документ взаимодействия фиксирует дату и время события, клиента, контактное лицо, вид коммуникации, краткое содержание и достигнутый результат. Список контактных лиц фильтруется по ранее выбранному клиенту. Реквизит следующего взаимодействия связывает завершенное действие с запланированным продолжением.",
    )
    add_body(
        doc,
        "Для защиты качества данных настроена проверка обязательного заполнения. У клиента обязательны наименование, телефон и электронная почта. У контактного лица обязательны ФИО, телефон и электронная почта. Во взаимодействии проверяются клиент, вид и содержание.",
    )

    add_heading(doc, "4 Реализованные функции")
    add_heading(doc, "4.1 Планирование и напоминания", level=2)
    add_body(
        doc,
        "Команда Запланировать взаимодействие открывает новую карточку документа. Пользователь задает дату, клиента, вид, содержание и момент напоминания. При запуске приложения система выбирает наступившие напоминания по незавершенным будущим взаимодействиям и показывает пользовательские оповещения. Оповещение содержит ссылку на соответствующий документ.",
    )
    add_heading(doc, "4.2 Отчет по активности", level=2)
    add_body(
        doc,
        "Отчет Активности клиентов построен на системе компоновки данных. Записи группируются по клиентам и сортируются по дате. В отчет выводятся дата и время, вид взаимодействия, краткое содержание и результат.",
    )
    add_body(doc, "Для быстрого визуального анализа используется цветовая индикация:")
    add_bullet(doc, "прошедшие события старше двух недель выделяются светло-серым цветом;")
    add_bullet(doc, "события последних двух недель выделяются светло-желтым цветом;")
    add_bullet(doc, "будущие взаимодействия выделяются светло-зеленым цветом.")

    add_heading(doc, "5 Демонстрационные данные")
    add_body(
        doc,
        "При первом запуске создается демонстрационный набор. Повторная инициализация не создает дубликаты: система ищет существующие элементы и документы перед записью.",
    )
    add_table(
        doc,
        ["Данные", "Количество", "Состав"],
        [
            ("Клиенты", "4", "Альфа, Бета, Гамма, Дельта"),
            ("Контактные лица", "4", "По одному контакту для каждого клиента"),
            ("Взаимодействия", "6", "Звонки, встречи, электронное письмо и демонстрация"),
            ("Прошедшие события", "2", "Связаны с будущими запланированными действиями"),
        ],
        [1.8, 1.0, 4.0],
    )

    add_heading(doc, "6 Проверка работоспособности")
    add_body(doc, "Перед подготовкой поставки выполнены следующие проверки:")
    add_bullet(doc, "генерация 24 файлов исходного кода и метаданных конфигурации;")
    add_bullet(doc, "разбор всех XML-файлов стандартным XML-парсером;")
    add_bullet(doc, "загрузка исходников в информационную базу и обновление конфигурации базы данных;")
    add_bullet(doc, "встроенная проверка 1С с результатом Ошибок не обнаружено;")
    add_bullet(doc, "запуск пользовательского режима и проверка трех разделов, списков, команды планирования и отчета;")
    add_bullet(doc, "проверка наличия шести взаимодействий и ссылок от двух прошедших действий к будущим.")

    add_heading(doc, "7 Установка и запуск")
    add_numbered(doc, 1, "Установить учебную платформу 1С Предприятие версии 8.3.21.1644 или совместимую версию.")
    add_numbered(doc, 2, "Создать пустую файловую информационную базу.")
    add_numbered(doc, 3, "Загрузить файл CRM_Z1.cf через конфигуратор командой Конфигурация Загрузить конфигурацию из файла.")
    add_numbered(doc, 4, "Обновить конфигурацию базы данных и запустить режим 1С Предприятие.")
    add_numbered(doc, 5, "Для полного восстановления готовой базы вместо файла конфигурации можно загрузить резервную копию CRM_Z1.dt.")

    add_heading(doc, "8 Состав поставки")
    add_table(
        doc,
        ["Компонент", "Назначение"],
        [
            ("build/CRM_Z1.cf", "Готовый файл конфигурации 1С"),
            ("build/CRM_Z1.dt", "Резервная копия информационной базы с демонстрационными данными"),
            ("src", "Иерархическая выгрузка исходников конфигурации"),
            ("tools/generate_config.py", "Воспроизводимый генератор XML и BSL"),
            ("tools/build.ps1", "Автоматическая загрузка, проверка и сборка поставки"),
        ],
        [2.5, 4.3],
        compact=True,
    )

    add_heading(doc, "9 Соответствие критериям оценки")
    add_body(
        doc,
        "Реализация сопоставлена с 31 критерием оценочной таблицы. Стандартный интерфейс 1С соответствует базовому уровню дизайна, поэтому ожидаемая итоговая оценка составляет 96 из 100 баллов.",
    )
    add_table(
        doc,
        ["Группа критериев", "Результат", "Баллы"],
        [
            ("Информационная база и разделы", "Выполнено", "3 из 3"),
            ("Дизайн интерфейса", "Стандартный интерфейс 1С", "1 из 5"),
            ("Клиенты и контактные лица", "Выполнено", "30 из 30"),
            ("Поля, связи и размещение взаимодействий", "Выполнено", "15 из 15"),
            ("Напоминания", "Выполнено", "13 из 13"),
            ("Отчет, группировка и цвета", "Выполнено", "29 из 29"),
            ("Демонстрационные данные", "Выполнено", "5 из 5"),
        ],
        [3.4, 2.1, 1.3],
    )

    add_heading(doc, "Заключение")
    add_body(
        doc,
        "В результате создана работоспособная учебная CRM-конфигурация для 1С Предприятия. Она охватывает ведение клиентов и контактных лиц, регистрацию и планирование взаимодействий, напоминания и отчетность. Исходники, готовая конфигурация и резервная копия базы позволяют проверить решение и воспроизвести сборку.",
    )

    for sec in doc.sections:
        add_page_number(sec.footer.paragraphs[0])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.core_properties.title = "Пояснительная записка к учебному проекту CRM Z1"
    doc.core_properties.subject = "Конфигурация CRM для 1С Предприятия"
    doc.core_properties.author = "Антон"
    doc.core_properties.keywords = "1С, CRM, продажи, маркетинг, сервис"
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build_document()
