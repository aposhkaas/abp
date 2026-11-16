#!/usr/bin/env python3
"""Generate the CRM training configuration source for 1C:Enterprise 8.3.21."""

from __future__ import annotations

import hashlib
import shutil
import textwrap
import uuid
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
FORMAT_VERSION = "2.14"
NAMESPACE = uuid.UUID("6e277395-73cf-4f9a-9802-0cd5c1678e86")

NS = (
    'xmlns="http://v8.1c.ru/8.3/MDClasses" '
    'xmlns:app="http://v8.1c.ru/8.2/managed-application/core" '
    'xmlns:cfg="http://v8.1c.ru/8.1/data/enterprise/current-config" '
    'xmlns:cmi="http://v8.1c.ru/8.2/managed-application/cmi" '
    'xmlns:ent="http://v8.1c.ru/8.1/data/enterprise" '
    'xmlns:lf="http://v8.1c.ru/8.2/managed-application/logform" '
    'xmlns:style="http://v8.1c.ru/8.1/data/ui/style" '
    'xmlns:sys="http://v8.1c.ru/8.1/data/ui/fonts/system" '
    'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
    'xmlns:v8ui="http://v8.1c.ru/8.1/data/ui" '
    'xmlns:web="http://v8.1c.ru/8.1/data/ui/colors/web" '
    'xmlns:win="http://v8.1c.ru/8.1/data/ui/colors/windows" '
    'xmlns:xen="http://v8.1c.ru/8.3/xcf/enums" '
    'xmlns:xpr="http://v8.1c.ru/8.3/xcf/predef" '
    'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
    'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)


def uid(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8-sig", newline="\n")


def synonym(value: str, indent: str = "\t\t\t") -> str:
    return (
        f"{indent}<Synonym>\n"
        f"{indent}\t<v8:item>\n"
        f"{indent}\t\t<v8:lang>ru</v8:lang>\n"
        f"{indent}\t\t<v8:content>{escape(value)}</v8:content>\n"
        f"{indent}\t</v8:item>\n"
        f"{indent}</Synonym>"
    )


def type_xml(type_name: str, length: int = 0) -> str:
    if type_name == "string":
        return (
            "<v8:Type>xs:string</v8:Type>"
            f"<v8:StringQualifiers><v8:Length>{length}</v8:Length>"
            "<v8:AllowedLength>Variable</v8:AllowedLength></v8:StringQualifiers>"
        )
    if type_name == "boolean":
        return "<v8:Type>xs:boolean</v8:Type>"
    if type_name == "datetime":
        return (
            "<v8:Type>xs:dateTime</v8:Type><v8:DateQualifiers>"
            "<v8:DateFractions>DateTime</v8:DateFractions></v8:DateQualifiers>"
        )
    return f"<v8:Type>{escape(type_name)}</v8:Type>"


def attribute(
    owner: str,
    name: str,
    title: str,
    data_type: str,
    *,
    length: int = 0,
    required: bool = False,
    multiline: bool = False,
    use: str | None = None,
    choice_link: tuple[str, str] | None = None,
    column: bool = False,
) -> str:
    link_xml = "<ChoiceParameterLinks/>"
    if choice_link:
        parameter, source = choice_link
        link_xml = (
            "<ChoiceParameterLinks><xr:Link>"
            f"<xr:DataPath>{escape(source)}</xr:DataPath>"
            f"<xr:ValueName>{escape(parameter)}</xr:ValueName>"
            "</xr:Link></ChoiceParameterLinks>"
        )
    use_xml = f"<Use>{use}</Use>" if use else ""
    fill_value_xml = "" if column else '<FillFromFillingValue>false</FillFromFillingValue><FillValue xsi:nil="true"/>'
    return f"""
\t\t\t<Attribute uuid="{uid(owner + '.Attribute.' + name)}">
\t\t\t\t<Properties>
\t\t\t\t\t<Name>{name}</Name>
{synonym(title, chr(9) * 5)}
\t\t\t\t\t<Comment/>
\t\t\t\t\t<Type>{type_xml(data_type, length)}</Type>
\t\t\t\t\t<PasswordMode>false</PasswordMode><Format/><EditFormat/><ToolTip/>
\t\t\t\t\t<MarkNegatives>false</MarkNegatives><Mask/>
\t\t\t\t\t<MultiLine>{str(multiline).lower()}</MultiLine><ExtendedEdit>{str(multiline).lower()}</ExtendedEdit>
\t\t\t\t\t<MinValue xsi:nil="true"/><MaxValue xsi:nil="true"/>
\t\t\t\t\t{fill_value_xml}
\t\t\t\t\t<FillChecking>{'ShowError' if required else 'DontCheck'}</FillChecking>
\t\t\t\t\t<ChoiceFoldersAndItems>Items</ChoiceFoldersAndItems>{link_xml}<ChoiceParameters/>
\t\t\t\t\t<QuickChoice>Auto</QuickChoice><CreateOnInput>Auto</CreateOnInput><ChoiceForm/><LinkByType/>
\t\t\t\t\t<ChoiceHistoryOnInput>Auto</ChoiceHistoryOnInput>{use_xml}
\t\t\t\t\t<Indexing>DontIndex</Indexing><FullTextSearch>Use</FullTextSearch><DataHistory>Use</DataHistory>
\t\t\t\t</Properties>
\t\t\t</Attribute>""".strip()


def tabular_section(owner: str, name: str, title: str, columns: list[tuple[str, str, str, int]]) -> str:
    generated = []
    for prefix, category in (("CatalogTabularSection", "TabularSection"), ("CatalogTabularSectionRow", "TabularSectionRow")):
        key = f"{owner}.{name}.{prefix}"
        generated.append(
            f'<xr:GeneratedType name="{prefix}.{owner}.{name}" category="{category}">'
            f'<xr:TypeId>{uid(key + ".type")}</xr:TypeId><xr:ValueId>{uid(key + ".value")}</xr:ValueId>'
            "</xr:GeneratedType>"
        )
    attrs = []
    for col_name, col_title, col_type, col_len in columns:
        attrs.append(attribute(f"{owner}.{name}", col_name, col_title, col_type, length=col_len, column=True))
    return f"""
\t\t\t<TabularSection uuid="{uid(owner + '.TabularSection.' + name)}">
\t\t\t\t<InternalInfo>{''.join(generated)}</InternalInfo>
\t\t\t\t<Properties><Name>{name}</Name>{synonym(title, chr(9) * 5)}<Comment/><ToolTip/><FillChecking>DontCheck</FillChecking></Properties>
\t\t\t\t<ChildObjects>
{chr(10).join(attrs)}
\t\t\t\t</ChildObjects>
\t\t\t</TabularSection>""".strip()


def generated_types(kind: str, name: str) -> str:
    definitions = {
        "Catalog": (("CatalogObject", "Object"), ("CatalogRef", "Ref"), ("CatalogSelection", "Selection"), ("CatalogList", "List"), ("CatalogManager", "Manager")),
        "Document": (("DocumentObject", "Object"), ("DocumentRef", "Ref"), ("DocumentSelection", "Selection"), ("DocumentList", "List"), ("DocumentManager", "Manager")),
        "Enum": (("EnumRef", "Ref"), ("EnumManager", "Manager"), ("EnumList", "List")),
        "Report": (("ReportObject", "Object"), ("ReportManager", "Manager")),
    }
    values = []
    for prefix, category in definitions[kind]:
        key = f"{kind}.{name}.{prefix}"
        values.append(
            f'<xr:GeneratedType name="{prefix}.{name}" category="{category}">'
            f'<xr:TypeId>{uid(key + ".type")}</xr:TypeId><xr:ValueId>{uid(key + ".value")}</xr:ValueId>'
            "</xr:GeneratedType>"
        )
    return "".join(values)


def standard_attributes(kind: str) -> str:
    names = {
        "Catalog": ("PredefinedDataName", "Predefined", "Ref", "DeletionMark", "IsFolder", "Owner", "Parent", "Description", "Code"),
        "Document": ("Posted", "Ref", "DeletionMark", "Date", "Number"),
    }[kind]
    return "<StandardAttributes>" + "".join(
        f'<xr:StandardAttribute name="{name}"><xr:LinkByType/><xr:FillChecking>DontCheck</xr:FillChecking>'
        '<xr:MultiLine>false</xr:MultiLine><xr:FillFromFillingValue>false</xr:FillFromFillingValue>'
        '<xr:CreateOnInput>Auto</xr:CreateOnInput><xr:MaxValue xsi:nil="true"/><xr:ToolTip/>'
        '<xr:ExtendedEdit>false</xr:ExtendedEdit><xr:Format/><xr:ChoiceForm/><xr:QuickChoice>Auto</xr:QuickChoice>'
        '<xr:ChoiceHistoryOnInput>Auto</xr:ChoiceHistoryOnInput><xr:EditFormat/><xr:PasswordMode>false</xr:PasswordMode>'
        '<xr:DataHistory>Use</xr:DataHistory><xr:MarkNegatives>false</xr:MarkNegatives><xr:MinValue xsi:nil="true"/>'
        '<xr:Synonym/><xr:Comment/><xr:FullTextSearch>Use</xr:FullTextSearch><xr:ChoiceParameterLinks/>'
        '<xr:FillValue xsi:nil="true"/><xr:Mask/><xr:ChoiceParameters/></xr:StandardAttribute>'
        for name in names
    ) + "</StandardAttributes>"


def catalog_xml(name: str, title: str, attrs: list[str], tables: list[str] | None = None, owner: str | None = None) -> str:
    owners = '<Owners/>' if not owner else f'<Owners><xr:Item xsi:type="xr:MDObjectRef">Catalog.{owner}</xr:Item></Owners>'
    children = "\n".join(attrs + (tables or []))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}">
\t<Catalog uuid="{uid('Catalog.' + name)}">
\t\t<InternalInfo>{generated_types('Catalog', name)}</InternalInfo>
\t\t<Properties>
\t\t\t<Name>{name}</Name>
{synonym(title)}
\t\t\t<Comment/><Hierarchical>false</Hierarchical><HierarchyType>HierarchyFoldersAndItems</HierarchyType>
\t\t\t<LimitLevelCount>false</LimitLevelCount><LevelCount>2</LevelCount><FoldersOnTop>true</FoldersOnTop>
\t\t\t<UseStandardCommands>true</UseStandardCommands>{owners}<SubordinationUse>ToItems</SubordinationUse>
\t\t\t<CodeLength>9</CodeLength><DescriptionLength>100</DescriptionLength><CodeType>String</CodeType>
\t\t\t<CodeAllowedLength>Variable</CodeAllowedLength><CodeSeries>WholeCatalog</CodeSeries>
\t\t\t<CheckUnique>true</CheckUnique><Autonumbering>true</Autonumbering><DefaultPresentation>AsDescription</DefaultPresentation>
\t\t\t{standard_attributes('Catalog')}<Characteristics/><PredefinedDataUpdate>Auto</PredefinedDataUpdate>
\t\t\t<EditType>InDialog</EditType><QuickChoice>true</QuickChoice><ChoiceMode>BothWays</ChoiceMode><InputByString/>
\t\t\t<SearchStringModeOnInputByString>Begin</SearchStringModeOnInputByString><FullTextSearchOnInputByString>DontUse</FullTextSearchOnInputByString>
\t\t\t<ChoiceDataGetModeOnInputByString>Directly</ChoiceDataGetModeOnInputByString>
\t\t\t<DefaultObjectForm/><DefaultFolderForm/><DefaultListForm/><DefaultChoiceForm/><DefaultFolderChoiceForm/>
\t\t\t<AuxiliaryObjectForm/><AuxiliaryFolderForm/><AuxiliaryListForm/><AuxiliaryChoiceForm/><AuxiliaryFolderChoiceForm/>
\t\t\t<IncludeHelpInContents>false</IncludeHelpInContents><BasedOn/><DataLockFields/><DataLockControlMode>Automatic</DataLockControlMode>
\t\t\t<FullTextSearch>Use</FullTextSearch><ObjectPresentation/><ExtendedObjectPresentation/><ListPresentation/><ExtendedListPresentation/>
\t\t\t<Explanation/><CreateOnInput>Use</CreateOnInput><ChoiceHistoryOnInput>Auto</ChoiceHistoryOnInput><DataHistory>DontUse</DataHistory>
\t\t\t<UpdateDataHistoryImmediatelyAfterWrite>false</UpdateDataHistoryImmediatelyAfterWrite>
\t\t\t<ExecuteAfterWriteDataHistoryVersionProcessing>false</ExecuteAfterWriteDataHistoryVersionProcessing>
\t\t</Properties>
\t\t<ChildObjects>
{children}
\t\t</ChildObjects>
\t</Catalog>
</MetaDataObject>"""


def enum_xml(name: str, title: str, values: list[tuple[str, str]]) -> str:
    children = []
    for value, value_title in values:
        children.append(
            f'<EnumValue uuid="{uid("Enum." + name + "." + value)}"><Properties><Name>{value}</Name>'
            f'{synonym(value_title, chr(9) * 5)}<Comment/></Properties></EnumValue>'
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}">
\t<Enum uuid="{uid('Enum.' + name)}"><InternalInfo>{generated_types('Enum', name)}</InternalInfo>
\t\t<Properties><Name>{name}</Name>{synonym(title)}<Comment/><UseStandardCommands>true</UseStandardCommands>
\t\t\t<Characteristics/><QuickChoice>true</QuickChoice><ChoiceMode>BothWays</ChoiceMode>
\t\t\t<DefaultListForm/><DefaultChoiceForm/><AuxiliaryListForm/><AuxiliaryChoiceForm/>
\t\t\t<ListPresentation/><ExtendedListPresentation/><Explanation/><ChoiceHistoryOnInput>Auto</ChoiceHistoryOnInput>
\t\t</Properties><ChildObjects>{''.join(children)}</ChildObjects>
\t</Enum>
</MetaDataObject>"""


def document_xml(name: str, title: str, attrs: list[str]) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}">
\t<Document uuid="{uid('Document.' + name)}"><InternalInfo>{generated_types('Document', name)}</InternalInfo>
\t\t<Properties><Name>{name}</Name>{synonym(title)}<Comment/><UseStandardCommands>true</UseStandardCommands>
\t\t\t<Numerator/><NumberType>String</NumberType><NumberLength>11</NumberLength><NumberAllowedLength>Variable</NumberAllowedLength>
\t\t\t<NumberPeriodicity>Year</NumberPeriodicity><CheckUnique>true</CheckUnique><Autonumbering>true</Autonumbering>
\t\t\t{standard_attributes('Document')}<Characteristics/><BasedOn/><InputByString/><CreateOnInput>Use</CreateOnInput>
\t\t\t<SearchStringModeOnInputByString>Begin</SearchStringModeOnInputByString><FullTextSearchOnInputByString>DontUse</FullTextSearchOnInputByString>
\t\t\t<ChoiceDataGetModeOnInputByString>Directly</ChoiceDataGetModeOnInputByString>
\t\t\t<DefaultObjectForm/><DefaultListForm/><DefaultChoiceForm/><AuxiliaryObjectForm/><AuxiliaryListForm/><AuxiliaryChoiceForm/>
\t\t\t<Posting>Deny</Posting><RealTimePosting>Deny</RealTimePosting><RegisterRecordsDeletion>AutoDelete</RegisterRecordsDeletion>
\t\t\t<RegisterRecordsWritingOnPost>WriteModified</RegisterRecordsWritingOnPost><SequenceFilling>AutoFill</SequenceFilling><RegisterRecords/>
\t\t\t<PostInPrivilegedMode>true</PostInPrivilegedMode><UnpostInPrivilegedMode>true</UnpostInPrivilegedMode>
\t\t\t<IncludeHelpInContents>false</IncludeHelpInContents><DataLockFields/><DataLockControlMode>Automatic</DataLockControlMode>
\t\t\t<FullTextSearch>Use</FullTextSearch><ObjectPresentation/><ExtendedObjectPresentation/><ListPresentation/><ExtendedListPresentation/>
\t\t\t<Explanation/><ChoiceHistoryOnInput>Auto</ChoiceHistoryOnInput><DataHistory>DontUse</DataHistory>
\t\t\t<UpdateDataHistoryImmediatelyAfterWrite>false</UpdateDataHistoryImmediatelyAfterWrite>
\t\t\t<ExecuteAfterWriteDataHistoryVersionProcessing>false</ExecuteAfterWriteDataHistoryVersionProcessing>
\t\t</Properties><ChildObjects>{''.join(attrs)}</ChildObjects>
\t</Document>
</MetaDataObject>"""


def subsystem_xml(name: str, title: str, content: list[str]) -> str:
    items = "".join(f'<xr:Item xsi:type="xr:MDObjectRef">{item}</xr:Item>' for item in content)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}">
\t<Subsystem uuid="{uid('Subsystem.' + name)}"><Properties><Name>{name}</Name>{synonym(title)}<Comment/>
\t\t<IncludeHelpInContents>true</IncludeHelpInContents><IncludeInCommandInterface>true</IncludeInCommandInterface>
\t\t<UseOneCommand>false</UseOneCommand><Explanation/><Picture/><Content>{items}</Content>
\t</Properties><ChildObjects/></Subsystem>
</MetaDataObject>"""


def common_module_xml(name: str, title: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}">
\t<CommonModule uuid="{uid('CommonModule.' + name)}"><Properties><Name>{name}</Name>{synonym(title)}<Comment/>
\t\t<Global>false</Global><ClientManagedApplication>false</ClientManagedApplication><Server>true</Server>
\t\t<ExternalConnection>false</ExternalConnection><ClientOrdinaryApplication>false</ClientOrdinaryApplication>
\t\t<ServerCall>true</ServerCall><Privileged>true</Privileged><ReturnValuesReuse>DontUse</ReturnValuesReuse>
\t</Properties></CommonModule>
</MetaDataObject>"""


def common_command_xml(name: str, title: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}">
\t<CommonCommand uuid="{uid('CommonCommand.' + name)}"><Properties><Name>{name}</Name>{synonym(title)}<Comment/>
\t\t<Group>ActionsPanelCreate</Group><Representation>Auto</Representation><ToolTip/><Picture/><Shortcut/>
\t\t<IncludeHelpInContents>false</IncludeHelpInContents><CommandParameterType/><ParameterUseMode>Single</ParameterUseMode>
\t\t<ModifiesData>true</ModifiesData><OnMainServerUnavalableBehavior>Auto</OnMainServerUnavalableBehavior>
\t</Properties></CommonCommand>
</MetaDataObject>"""


def report_xml() -> str:
    name = "АктивностиКлиентов"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}">
\t<Report uuid="{uid('Report.' + name)}"><InternalInfo>{generated_types('Report', name)}</InternalInfo>
\t\t<Properties><Name>{name}</Name>{synonym('Активности клиентов')}<Comment/><UseStandardCommands>true</UseStandardCommands>
\t\t\t<DefaultForm/><AuxiliaryForm/><MainDataCompositionSchema>Report.{name}.Template.ОсновнаяСхемаКомпоновкиДанных</MainDataCompositionSchema>
\t\t\t<DefaultSettingsForm/><AuxiliarySettingsForm/><DefaultVariantForm/><VariantsStorage/><SettingsStorage/>
\t\t\t<IncludeHelpInContents>false</IncludeHelpInContents><ExtendedPresentation/><Explanation/>
\t\t</Properties><ChildObjects><Template>ОсновнаяСхемаКомпоновкиДанных</Template></ChildObjects>
\t</Report>
</MetaDataObject>"""


def dcs_xml() -> str:
    fields = [
        ("Клиент", "Клиент"), ("Дата", "Дата и время"), ("ВидВзаимодействия", "Вид взаимодействия"),
        ("КраткоеСодержание", "Краткое содержание"), ("Результат", "Результат"), ("Категория", "Категория")
    ]
    field_xml = "".join(
        f'<field xsi:type="DataSetFieldField"><dataPath>{name}</dataPath><field>{name}</field>'
        f'<title xsi:type="v8:LocalStringType"><v8:item><v8:lang>ru</v8:lang><v8:content>{title}</v8:content></v8:item></title></field>'
        for name, title in fields
    )
    selection_xml = "".join(
        f'<dcsset:item xsi:type="dcsset:SelectedItemField"><dcsset:field>{name}</dcsset:field></dcsset:item>'
        for name, _ in fields[:-1]
    )
    query = escape(textwrap.dedent("""
        ВЫБРАТЬ
            Взаимодействие.Клиент КАК Клиент,
            Взаимодействие.Дата КАК Дата,
            Взаимодействие.ВидВзаимодействия КАК ВидВзаимодействия,
            Взаимодействие.КраткоеСодержание КАК КраткоеСодержание,
            Взаимодействие.Результат КАК Результат,
            ВЫБОР
                КОГДА Взаимодействие.Дата < &ГраницаДвухНедель ТОГДА "Прошедшее"
                КОГДА Взаимодействие.Дата <= &ТекущаяДата ТОГДА "ПоследниеДвеНедели"
                ИНАЧЕ "Будущее"
            КОНЕЦ КАК Категория
        ИЗ Документ.Взаимодействие КАК Взаимодействие
    """).strip())

    parameters = "".join(
        f'<parameter><name>{name}</name><title xsi:type="v8:LocalStringType"><v8:item><v8:lang>ru</v8:lang>'
        f'<v8:content>{title}</v8:content></v8:item></title><valueType><v8:Type>xs:dateTime</v8:Type>'
        '<v8:DateQualifiers><v8:DateFractions>DateTime</v8:DateFractions></v8:DateQualifiers></valueType>'
        '<value xsi:type="xs:dateTime">0001-01-01T00:00:00</value><useRestriction>false</useRestriction></parameter>'
        for name, title in (("ТекущаяДата", "Текущая дата"), ("ГраницаДвухНедель", "Граница двух недель"))
    )

    def appearance(category: str, color: str) -> str:
        return f"""<dcsset:item><dcsset:filter><dcsset:item xsi:type="dcsset:FilterItemComparison">
        <dcsset:left xsi:type="dcscor:Field">Категория</dcsset:left><dcsset:comparisonType>Equal</dcsset:comparisonType>
        <dcsset:right xsi:type="xs:string">{category}</dcsset:right></dcsset:item></dcsset:filter>
        <dcsset:appearance><dcscor:item xsi:type="dcsset:SettingsParameterValue"><dcscor:parameter>ЦветФона</dcscor:parameter>
        <dcscor:value xsi:type="v8ui:Color">{color}</dcscor:value></dcscor:item></dcsset:appearance></dcsset:item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<DataCompositionSchema xmlns="http://v8.1c.ru/8.1/data-composition-system/schema"
 xmlns:dcscom="http://v8.1c.ru/8.1/data-composition-system/common"
 xmlns:dcscor="http://v8.1c.ru/8.1/data-composition-system/core"
 xmlns:dcsset="http://v8.1c.ru/8.1/data-composition-system/settings"
 xmlns:v8="http://v8.1c.ru/8.1/data/core" xmlns:v8ui="http://v8.1c.ru/8.1/data/ui"
 xmlns:style="http://v8.1c.ru/8.1/data/ui/style" xmlns:web="http://v8.1c.ru/8.1/data/ui/colors/web"
 xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
\t<dataSource><name>ИсточникДанных</name><dataSourceType>Local</dataSourceType></dataSource>
\t<dataSet xsi:type="DataSetQuery"><name>Активности</name>{field_xml}<dataSource>ИсточникДанных</dataSource><query>{query}</query></dataSet>
\t{parameters}
\t<settingsVariant><dcsset:name>Основной</dcsset:name><dcsset:presentation xsi:type="xs:string">Основной</dcsset:presentation>
\t\t<dcsset:settings><dcsset:selection>{selection_xml}</dcsset:selection>
\t\t\t<dcsset:order><dcsset:item xsi:type="dcsset:OrderItemField"><dcsset:field>Дата</dcsset:field><dcsset:orderType>Asc</dcsset:orderType></dcsset:item></dcsset:order>
\t\t\t<dcsset:conditionalAppearance>{appearance('Прошедшее', 'web:LightGray')}{appearance('ПоследниеДвеНедели', 'web:LightYellow')}{appearance('Будущее', 'web:PaleGreen')}</dcsset:conditionalAppearance>
\t\t\t<dcsset:item xsi:type="dcsset:StructureItemGroup"><dcsset:name>Клиенты</dcsset:name><dcsset:groupItems>
\t\t\t\t<dcsset:item xsi:type="dcsset:GroupItemField"><dcsset:field>Клиент</dcsset:field><dcsset:groupType>Items</dcsset:groupType>
\t\t\t\t<dcsset:periodAdditionType>None</dcsset:periodAdditionType><dcsset:periodAdditionBegin xsi:type="xs:dateTime">0001-01-01T00:00:00</dcsset:periodAdditionBegin>
\t\t\t\t<dcsset:periodAdditionEnd xsi:type="xs:dateTime">0001-01-01T00:00:00</dcsset:periodAdditionEnd></dcsset:item></dcsset:groupItems>
\t\t\t\t<dcsset:order><dcsset:item xsi:type="dcsset:OrderItemAuto"/></dcsset:order><dcsset:selection><dcsset:item xsi:type="dcsset:SelectedItemAuto"/></dcsset:selection>
\t\t\t\t<dcsset:item xsi:type="dcsset:StructureItemGroup"><dcsset:name>ДетальныеЗаписи</dcsset:name>
\t\t\t\t<dcsset:order><dcsset:item xsi:type="dcsset:OrderItemAuto"/></dcsset:order><dcsset:selection><dcsset:item xsi:type="dcsset:SelectedItemAuto"/></dcsset:selection></dcsset:item>
\t\t\t</dcsset:item></dcsset:settings>
\t</settingsVariant>
</DataCompositionSchema>"""


def configuration_xml(children: list[tuple[str, str]]) -> str:
    class_ids = (
        "9cd510cd-abfc-11d4-9434-004095e12fc7", "9fcd25a0-4822-11d4-9414-008048da11f9",
        "e3687481-0a87-462c-a166-9f34594f9bba", "9de14907-ec23-4a07-96f0-85521cb6b53b",
        "51f2d5d8-ea4d-4064-8892-82951750031e", "e68182ea-4237-4383-967f-90c1e3370bc7",
        "fb282519-d103-4dd3-bc12-cb271d631dfc",
    )
    contained = "".join(
        f'<xr:ContainedObject><xr:ClassId>{class_id}</xr:ClassId><xr:ObjectId>{uid("Configuration.Contained." + str(i))}</xr:ObjectId></xr:ContainedObject>'
        for i, class_id in enumerate(class_ids)
    )
    child_xml = "".join(f"<{tag}>{name}</{tag}>" for tag, name in children)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}">
\t<Configuration uuid="{uid('Configuration.CRMZ1')}"><InternalInfo>{contained}</InternalInfo>
\t\t<Properties><Name>CRMZ1</Name>{synonym('CRM: продажи, маркетинг и сервис')}<Comment/><NamePrefix/>
\t\t\t<ConfigurationExtensionCompatibilityMode>Version8_3_21</ConfigurationExtensionCompatibilityMode><DefaultRunMode>ManagedApplication</DefaultRunMode>
\t\t\t<UsePurposes><v8:Value xsi:type="app:ApplicationUsePurpose">PlatformApplication</v8:Value></UsePurposes><ScriptVariant>Russian</ScriptVariant>
\t\t\t<DefaultRoles/><Vendor>Учебный проект</Vendor><Version>1.0.0</Version><UpdateCatalogAddress/><IncludeHelpInContents>false</IncludeHelpInContents>
\t\t\t<UseManagedFormInOrdinaryApplication>false</UseManagedFormInOrdinaryApplication><UseOrdinaryFormInManagedApplication>false</UseOrdinaryFormInManagedApplication>
\t\t\t<AdditionalFullTextSearchDictionaries/><CommonSettingsStorage/><ReportsUserSettingsStorage/><ReportsVariantsStorage/><FormDataSettingsStorage/>
\t\t\t<DynamicListsUserSettingsStorage/><URLExternalDataStorage/><Content/><DefaultReportForm/><DefaultReportVariantForm/><DefaultReportSettingsForm/>
\t\t\t<DefaultDynamicListSettingsForm/><DefaultSearchForm/><DefaultDataHistoryChangeHistoryForm/><DefaultDataHistoryVersionDataForm/>
\t\t\t<DefaultDataHistoryVersionDifferencesForm/><DefaultCollaborationSystemUsersChoiceForm/><RequiredMobileApplicationPermissions/>
\t\t\t<UsedMobileApplicationFunctionalities/><StandaloneConfigurationRestrictionRoles/><MobileApplicationURLs/><MainClientApplicationWindowMode>Normal</MainClientApplicationWindowMode>
\t\t\t<DefaultInterface/><DefaultStyle/><DefaultLanguage>Language.Русский</DefaultLanguage><BriefInformation/><DetailedInformation/><Copyright/>
\t\t\t<VendorInformationAddress/><ConfigurationInformationAddress/><DataLockControlMode>Managed</DataLockControlMode><ObjectAutonumerationMode>NotAutoFree</ObjectAutonumerationMode>
\t\t\t<ModalityUseMode>DontUse</ModalityUseMode><SynchronousPlatformExtensionAndAddInCallUseMode>DontUse</SynchronousPlatformExtensionAndAddInCallUseMode>
\t\t\t<InterfaceCompatibilityMode>Taxi</InterfaceCompatibilityMode><CompatibilityMode>Version8_3_21</CompatibilityMode><DefaultConstantsForm/>
\t\t</Properties><ChildObjects>{child_xml}</ChildObjects>
\t</Configuration>
</MetaDataObject>"""


def language_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}"><Language uuid="{uid('Language.Russian')}"><Properties><Name>Русский</Name>
{synonym('Русский')}<Comment/><LanguageCode>ru</LanguageCode></Properties></Language></MetaDataObject>"""


CLIENT_MODULE = """
Процедура ОбработкаПроверкиЗаполнения(Отказ, ПроверяемыеРеквизиты)
    ПроверяемыеРеквизиты.Добавить("Наименование");
    ПроверяемыеРеквизиты.Добавить("Телефон");
    ПроверяемыеРеквизиты.Добавить("ЭлектроннаяПочта");
КонецПроцедуры
"""

CONTACT_MODULE = """
Процедура ОбработкаПроверкиЗаполнения(Отказ, ПроверяемыеРеквизиты)
    ПроверяемыеРеквизиты.Добавить("Наименование");
    ПроверяемыеРеквизиты.Добавить("Телефон");
    ПроверяемыеРеквизиты.Добавить("ЭлектроннаяПочта");
КонецПроцедуры
"""

DOCUMENT_MODULE = """
Процедура ОбработкаПроверкиЗаполнения(Отказ, ПроверяемыеРеквизиты)
    ПроверяемыеРеквизиты.Добавить("Клиент");
    ПроверяемыеРеквизиты.Добавить("ВидВзаимодействия");
    ПроверяемыеРеквизиты.Добавить("КраткоеСодержание");
КонецПроцедуры
"""

SERVER_MODULE = """
Функция НайтиИлиСоздатьКлиента(Наименование, Источник, Телефон, Почта, Комментарий) Экспорт
    Ссылка = Справочники.Клиенты.НайтиПоНаименованию(Наименование);
    Если Ссылка.Пустая() Тогда
        Объект = Справочники.Клиенты.СоздатьЭлемент();
        Объект.Наименование = Наименование;
        Объект.ИсточникПоявления = Источник;
        Объект.Телефон = Телефон;
        Объект.ЭлектроннаяПочта = Почта;
        Объект.Комментарий = Комментарий;
        СтрокаТелефона = Объект.Телефоны.Добавить(); СтрокаТелефона.НомерТелефона = Телефон;
        СтрокаПочты = Объект.ЭлектронныеАдреса.Добавить(); СтрокаПочты.АдресПочты = Почта;
        Объект.Записать();
        Ссылка = Объект.Ссылка;
    КонецЕсли;
    Возврат Ссылка;
КонецФункции

Процедура СоздатьКонтакт(Клиент, ФИО, Телефон, Почта, Роль, Основной)
    Если Не Справочники.КонтактныеЛица.НайтиПоНаименованию(ФИО, Истина, Клиент).Пустая() Тогда Возврат; КонецЕсли;
    Контакт = Справочники.КонтактныеЛица.СоздатьЭлемент();
    Контакт.Владелец = Клиент; Контакт.Клиент = Клиент; Контакт.Наименование = ФИО;
    Контакт.Телефон = Телефон; Контакт.ЭлектроннаяПочта = Почта; Контакт.Роль = Роль;
    Контакт.ОсновноеКонтактноеЛицо = Основной; Контакт.Комментарий = "Демонстрационное контактное лицо";
    Контакт.Записать();
КонецПроцедуры

Функция СоздатьВзаимодействие(Клиент, СмещениеДней, Вид, Содержание, Результат, НапомнитьЗаЧасов)
    Запрос = Новый Запрос;
    Запрос.Текст = "ВЫБРАТЬ ПЕРВЫЕ 1 Взаимодействие.Ссылка ИЗ Документ.Взаимодействие КАК Взаимодействие ГДЕ Взаимодействие.Клиент = &Клиент И ВЫРАЗИТЬ(Взаимодействие.КраткоеСодержание КАК СТРОКА(200)) = &Содержание";
    Запрос.УстановитьПараметр("Клиент", Клиент);
    Запрос.УстановитьПараметр("Содержание", Содержание);
    Выборка = Запрос.Выполнить().Выбрать();
    Если Выборка.Следующий() Тогда Возврат Выборка.Ссылка; КонецЕсли;
    Документ = Документы.Взаимодействие.СоздатьДокумент();
    Документ.Дата = НачалоДня(ТекущаяДата() + СмещениеДней * 86400) + 12 * 3600;
    Документ.Клиент = Клиент; Документ.ВидВзаимодействия = Вид; Документ.КраткоеСодержание = Содержание;
    Документ.Результат = Результат; Документ.Напомнить = Документ.Дата - НапомнитьЗаЧасов * 3600;
    Документ.Выполнено = СмещениеДней < 0; Документ.Записать();
    Возврат Документ.Ссылка;
КонецФункции

Процедура УстановитьСледующееВзаимодействие(ТекущееВзаимодействие, СледующееВзаимодействие)
    Если ТекущееВзаимодействие.Пустая() Или СледующееВзаимодействие.Пустая() Тогда Возврат; КонецЕсли;
    ОбъектВзаимодействия = ТекущееВзаимодействие.ПолучитьОбъект();
    Если ОбъектВзаимодействия.СледующееВзаимодействие <> СледующееВзаимодействие Тогда
        ОбъектВзаимодействия.СледующееВзаимодействие = СледующееВзаимодействие;
        ОбъектВзаимодействия.Записать();
    КонецЕсли;
КонецПроцедуры

Процедура ИнициализироватьДемонстрационныеДанные() Экспорт
    Клиент1 = НайтиИлиСоздатьКлиента("Альфа", Перечисления.ИсточникиПоявления.Реклама, "+7 913 000-10-01", "office@alfa.example", "Производственная компания");
    Клиент2 = НайтиИлиСоздатьКлиента("Бета", Перечисления.ИсточникиПоявления.Рекомендация, "+7 913 000-10-02", "hello@beta.example", "Розничная сеть");
    Клиент3 = НайтиИлиСоздатьКлиента("Гамма", Перечисления.ИсточникиПоявления.Сайт, "+7 913 000-10-03", "info@gamma.example", "Сервисная компания");
    Клиент4 = НайтиИлиСоздатьКлиента("Дельта", Перечисления.ИсточникиПоявления.Выставка, "+7 913 000-10-04", "sales@delta.example", "Оптовый клиент");
    СоздатьКонтакт(Клиент1, "Анна Петрова", "+7 913 100-01-01", "a.petrova@alfa.example", Перечисления.РолиКонтактныхЛиц.ЛицоПринимающееРешение, Истина);
    СоздатьКонтакт(Клиент2, "Борис Иванов", "+7 913 100-01-02", "b.ivanov@beta.example", Перечисления.РолиКонтактныхЛиц.Закупщик, Истина);
    СоздатьКонтакт(Клиент3, "Вера Соколова", "+7 913 100-01-03", "v.sokolova@gamma.example", Перечисления.РолиКонтактныхЛиц.ТехническийСпециалист, Истина);
    СоздатьКонтакт(Клиент4, "Глеб Морозов", "+7 913 100-01-04", "g.morozov@delta.example", Перечисления.РолиКонтактныхЛиц.Закупщик, Истина);
    Взаимодействие1 = СоздатьВзаимодействие(Клиент1, -30, Перечисления.ВидыВзаимодействий.Звонок, "Первичный звонок", Перечисления.РезультатыВзаимодействий.Успешно, 1);
    Взаимодействие2 = СоздатьВзаимодействие(Клиент2, -5, Перечисления.ВидыВзаимодействий.Встреча, "Презентация решения", Перечисления.РезультатыВзаимодействий.ТребуетсяПродолжение, 2);
    Взаимодействие3 = СоздатьВзаимодействие(Клиент3, 1, Перечисления.ВидыВзаимодействий.ЭлектронноеПисьмо, "Отправить коммерческое предложение", Перечисления.РезультатыВзаимодействий.НеОпределено, 3);
    Взаимодействие4 = СоздатьВзаимодействие(Клиент4, 3, Перечисления.ВидыВзаимодействий.Встреча, "Обсудить условия договора", Перечисления.РезультатыВзаимодействий.НеОпределено, 4);
    Взаимодействие5 = СоздатьВзаимодействие(Клиент1, 7, Перечисления.ВидыВзаимодействий.Демонстрация, "Провести демонстрацию", Перечисления.РезультатыВзаимодействий.НеОпределено, 6);
    Взаимодействие6 = СоздатьВзаимодействие(Клиент2, 14, Перечисления.ВидыВзаимодействий.Звонок, "Контрольный звонок", Перечисления.РезультатыВзаимодействий.НеОпределено, 12);
    УстановитьСледующееВзаимодействие(Взаимодействие1, Взаимодействие5);
    УстановитьСледующееВзаимодействие(Взаимодействие2, Взаимодействие6);
КонецПроцедуры

Функция ПолучитьАктуальныеНапоминания() Экспорт
    Запрос = Новый Запрос;
    Запрос.Текст = "ВЫБРАТЬ ПЕРВЫЕ 20 Взаимодействие.Ссылка, Взаимодействие.Клиент, Взаимодействие.ВидВзаимодействия, Взаимодействие.Дата ИЗ Документ.Взаимодействие КАК Взаимодействие ГДЕ Взаимодействие.Выполнено = ЛОЖЬ И Взаимодействие.Напомнить <= &Сейчас И Взаимодействие.Дата >= &Сейчас УПОРЯДОЧИТЬ ПО Взаимодействие.Дата";
    Запрос.УстановитьПараметр("Сейчас", ТекущаяДата());
    Возврат Запрос.Выполнить().Выгрузить();
КонецФункции
"""

MANAGED_APP_MODULE = """
Процедура ПриНачалеРаботыСистемы()
    Попытка
        CRMСервер.ИнициализироватьДемонстрационныеДанные();
        Напоминания = CRMСервер.ПолучитьАктуальныеНапоминания();
        Для Каждого Напоминание Из Напоминания Цикл
            Текст = СтрШаблон("%1: %2 (%3)", Напоминание.Клиент, Напоминание.ВидВзаимодействия, Формат(Напоминание.Дата, "ДФ=dd.MM.yyyy HH:mm"));
            ПоказатьОповещениеПользователя(Текст, Напоминание.Ссылка, "Запланированное взаимодействие");
        КонецЦикла;
    Исключение
        Сообщить("Не удалось подготовить демонстрационные данные: " + ОписаниеОшибки());
    КонецПопытки;
КонецПроцедуры
"""

REPORT_MODULE = """
Процедура ПриКомпоновкеРезультата(ДокументРезультат, ДанныеРасшифровки, СтандартнаяОбработка)
    КомпоновщикНастроек.Настройки.ПараметрыДанных.УстановитьЗначениеПараметра("ТекущаяДата", ТекущаяДата());
    КомпоновщикНастроек.Настройки.ПараметрыДанных.УстановитьЗначениеПараметра("ГраницаДвухНедель", НачалоДня(ТекущаяДата() - 14 * 86400));
КонецПроцедуры
"""

PLAN_INTERACTION_COMMAND = """
&НаКлиенте
Процедура ОбработкаКоманды(ПараметрКоманды, ПараметрыВыполненияКоманды)
    ОткрытьФорму("Документ.Взаимодействие.ФормаОбъекта", , ПараметрыВыполненияКоманды.Источник);
КонецПроцедуры
"""


def main() -> None:
    if SRC != ROOT / "src":
        raise RuntimeError("Unexpected generation target")
    if SRC.exists():
        shutil.rmtree(SRC)
    SRC.mkdir(parents=True)

    enums = {
        "ИсточникиПоявления": ("Источники появления", [("Реклама", "Реклама"), ("Рекомендация", "Рекомендация"), ("Сайт", "Сайт"), ("Выставка", "Выставка"), ("Другое", "Другое")]),
        "РолиКонтактныхЛиц": ("Роли контактных лиц", [("ЛицоПринимающееРешение", "Лицо, принимающее решение"), ("Закупщик", "Закупщик"), ("ТехническийСпециалист", "Технический специалист"), ("Другое", "Другое")]),
        "ВидыВзаимодействий": ("Виды взаимодействий", [("Звонок", "Звонок"), ("Встреча", "Встреча"), ("ЭлектронноеПисьмо", "Электронное письмо"), ("Демонстрация", "Демонстрация"), ("Другое", "Другое")]),
        "РезультатыВзаимодействий": ("Результаты взаимодействий", [("НеОпределено", "Не определено"), ("Успешно", "Успешно"), ("ТребуетсяПродолжение", "Требуется продолжение"), ("Отказ", "Отказ")]),
    }

    client_attrs = [
        attribute("Клиенты", "ИсточникПоявления", "Источник появления", "cfg:EnumRef.ИсточникиПоявления"),
        attribute("Клиенты", "Телефон", "Основной телефон", "string", length=50, required=True),
        attribute("Клиенты", "ЭлектроннаяПочта", "Основная электронная почта", "string", length=100, required=True),
        attribute("Клиенты", "Комментарий", "Комментарий", "string", length=0, multiline=True),
    ]
    client_tables = [
        tabular_section("Клиенты", "Телефоны", "Телефоны", [("НомерТелефона", "Номер телефона", "string", 50)]),
        tabular_section("Клиенты", "ЭлектронныеАдреса", "Электронные адреса", [("АдресПочты", "Адрес электронной почты", "string", 100)]),
    ]
    contact_attrs = [
        attribute("КонтактныеЛица", "Клиент", "Клиент", "cfg:CatalogRef.Клиенты", required=True),
        attribute("КонтактныеЛица", "Телефон", "Телефон", "string", length=50, required=True),
        attribute("КонтактныеЛица", "ЭлектроннаяПочта", "Электронная почта", "string", length=100, required=True),
        attribute("КонтактныеЛица", "Роль", "Роль", "cfg:EnumRef.РолиКонтактныхЛиц"),
        attribute("КонтактныеЛица", "ОсновноеКонтактноеЛицо", "Основное контактное лицо", "boolean"),
        attribute("КонтактныеЛица", "Комментарий", "Комментарий", "string", length=0, multiline=True),
    ]
    interaction_attrs = [
        attribute("Взаимодействие", "Клиент", "Клиент", "cfg:CatalogRef.Клиенты", required=True),
        attribute("Взаимодействие", "КонтактноеЛицо", "Контактное лицо", "cfg:CatalogRef.КонтактныеЛица", choice_link=("Отбор.Владелец", "Объект.Клиент")),
        attribute("Взаимодействие", "ВидВзаимодействия", "Вид взаимодействия", "cfg:EnumRef.ВидыВзаимодействий", required=True),
        attribute("Взаимодействие", "КраткоеСодержание", "Краткое содержание", "string", length=0, required=True, multiline=True),
        attribute("Взаимодействие", "Результат", "Достигнутый результат", "cfg:EnumRef.РезультатыВзаимодействий"),
        attribute("Взаимодействие", "СледующееВзаимодействие", "Следующее запланированное взаимодействие", "cfg:DocumentRef.Взаимодействие"),
        attribute("Взаимодействие", "Напомнить", "Напомнить", "datetime"),
        attribute("Взаимодействие", "Выполнено", "Выполнено", "boolean"),
    ]

    write(SRC / "Languages" / "Русский.xml", language_xml())
    write(SRC / "Catalogs" / "Клиенты.xml", catalog_xml("Клиенты", "Клиенты", client_attrs, client_tables))
    write(SRC / "Catalogs" / "Клиенты" / "Ext" / "ObjectModule.bsl", CLIENT_MODULE)
    write(SRC / "Catalogs" / "КонтактныеЛица.xml", catalog_xml("КонтактныеЛица", "Контактные лица", contact_attrs, owner="Клиенты"))
    write(SRC / "Catalogs" / "КонтактныеЛица" / "Ext" / "ObjectModule.bsl", CONTACT_MODULE)
    for name, (title, values) in enums.items():
        write(SRC / "Enums" / f"{name}.xml", enum_xml(name, title, values))
    write(SRC / "Documents" / "Взаимодействие.xml", document_xml("Взаимодействие", "Взаимодействие", interaction_attrs))
    write(SRC / "Documents" / "Взаимодействие" / "Ext" / "ObjectModule.bsl", DOCUMENT_MODULE)
    write(SRC / "Reports" / "АктивностиКлиентов.xml", report_xml())
    write(SRC / "Reports" / "АктивностиКлиентов" / "Ext" / "ObjectModule.bsl", REPORT_MODULE)
    write(SRC / "Reports" / "АктивностиКлиентов" / "Templates" / "ОсновнаяСхемаКомпоновкиДанных.xml", f'''<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="{FORMAT_VERSION}"><Template uuid="{uid('Report.Activity.Template.DCS')}"><Properties>
<Name>ОсновнаяСхемаКомпоновкиДанных</Name>{synonym('Основная схема компоновки данных')}<Comment/><TemplateType>DataCompositionSchema</TemplateType>
</Properties></Template></MetaDataObject>''')
    write(SRC / "Reports" / "АктивностиКлиентов" / "Templates" / "ОсновнаяСхемаКомпоновкиДанных" / "Ext" / "Template.xml", dcs_xml())
    write(SRC / "CommonModules" / "CRMСервер.xml", common_module_xml("CRMСервер", "CRM сервер"))
    write(SRC / "CommonModules" / "CRMСервер" / "Ext" / "Module.bsl", SERVER_MODULE)
    write(SRC / "CommonCommands" / "ЗапланироватьВзаимодействие.xml", common_command_xml("ЗапланироватьВзаимодействие", "Запланировать взаимодействие"))
    write(SRC / "CommonCommands" / "ЗапланироватьВзаимодействие" / "Ext" / "CommandModule.bsl", PLAN_INTERACTION_COMMAND)
    write(SRC / "Ext" / "ManagedApplicationModule.bsl", MANAGED_APP_MODULE)

    sales_content = ["Catalog.Клиенты", "Catalog.КонтактныеЛица", "Document.Взаимодействие", "Report.АктивностиКлиентов", "CommonCommand.ЗапланироватьВзаимодействие"]
    write(SRC / "Subsystems" / "Продажи.xml", subsystem_xml("Продажи", "Продажи", sales_content))
    write(SRC / "Subsystems" / "Маркетинг.xml", subsystem_xml("Маркетинг", "Маркетинг", sales_content))
    write(SRC / "Subsystems" / "Сервис.xml", subsystem_xml("Сервис", "Сервис", ["Catalog.Клиенты", "Catalog.КонтактныеЛица", "Document.Взаимодействие", "CommonCommand.ЗапланироватьВзаимодействие"]))

    children: list[tuple[str, str]] = [("Language", "Русский")]
    children.extend(("Subsystem", name) for name in ("Продажи", "Маркетинг", "Сервис"))
    children.append(("CommonModule", "CRMСервер"))
    children.append(("CommonCommand", "ЗапланироватьВзаимодействие"))
    children.extend(("Catalog", name) for name in ("Клиенты", "КонтактныеЛица"))
    children.extend(("Enum", name) for name in enums)
    children.append(("Document", "Взаимодействие"))
    children.append(("Report", "АктивностиКлиентов"))
    write(SRC / "Configuration.xml", configuration_xml(children))

    digest = hashlib.sha256("\n".join(str(path.relative_to(SRC)) for path in sorted(SRC.rglob("*")) if path.is_file()).encode()).hexdigest()
    print(f"Generated {sum(1 for p in SRC.rglob('*') if p.is_file())} files; manifest sha256={digest}")


if __name__ == "__main__":
    main()
