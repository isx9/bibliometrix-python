from www.services import *
from functions.get_status import *


def create_plotly_table(sorted_columns, dpi=300):
    """Create a Plotly table visualization for metadata completeness."""
    metadata = [col for col, _, _, _, _ in sorted_columns]
    descriptions = [desc for _, desc, _, _, _ in sorted_columns]
    counts = [cnt for _, _, cnt, _, _ in sorted_columns]
    percentages = [f"{pct:.2f}%" for _, _, _, pct, _ in sorted_columns]
    statuses = [status for _, _, _, _, status in sorted_columns]

    status_colors = {
        "Excellent": "lightgreen",
        "Good": "yellow",
        "Fair": "orange",
        "Poor": "red"
    }
    color_cells = [status_colors.get(s, "white") for s in statuses]

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["<b>Metadata</b>", "<b>Description</b>", "<b>Missing Counts</b>", "<b>Missing %</b>", "<b>Status</b>"],
            line_color='darkslategray',
            fill_color='#5567BB',
            align='center',
            font=dict(color='black', size=13)
        ),
        cells=dict(
            values=[metadata, descriptions, counts, percentages, statuses],
            line_color='darkslategray',
            fill_color=[["white"] * len(metadata)] * 4 + [color_cells],
            align='center',
            font=dict(color='black', size=12),
            height=30
        )
    )])

    table_height = 120 + len(metadata) * 30

    fig.update_layout(
        title_text="Missing Data Table",
        title_font_size=0.08 * dpi,
        title_font_color="black",
        title_yanchor='top',
        width=1400,
        height=table_height,
        margin=dict(l=10, r=10, t=70, b=10),
        paper_bgcolor="white",
    )

    fig.add_layout_image(
        dict(
            source="https://raw.githubusercontent.com/massimoaria/bibliometrix/master/logo.png",
            xref="paper", yref="paper",
            x=1, y=1,
            sizex=0.07, sizey=0.07,
            xanchor="right", yanchor="bottom"
        )
    )

    return fig


def get_table(database, df, dpi=300, filter=False, modal=True):
    """
    Display a table showing the completeness of bibliographic metadata.

    Args:
        database: The name of the database.
        df: A DataFrame object containing the data.
        filter: A boolean indicating whether to filter the data.
        modal: Whether to show a modal dialog with the completeness table.

    Returns:
        A tuple of (DataTable HTML, table HTML string, Plotly figure) if data
        is available, otherwise a message indicating no data.
    """
    # PATCH 1: df.get() is not a standard pandas method — it was a custom method
    # of a wrapper object that has since been removed. Using df.copy() to work
    # on a copy and avoid mutating the original DataFrame passed by the caller.
    data = df.copy()

    table_html = ""
    fig = None
    if not filter:
        total_rows = len(data)

        column_descriptions = {
            "AB": "Abstract",
            "AU": "Authors",
            "AU_UN": "Authors University",
            "DB": "Source",
            "DE": "Keywords",
            "DT": "Document Type",
            "LA": "Language",
            "PU": "Publisher",
            "PY": "Publication Year",
            "RP": "Correspondence Address",
            "SC": "Fields of Study",
            "SO": "Journal",
            "SR": "Authors, Publication Year and Journal",
            "TC": "Time Cited",
            "TI": "Title",
            "UT": "Publication ID",
            "C1": "Authors Affiliations",
            "CR": "Cited References",
            "OI": "Author's ORCID",
            "AU1_UN": "First Author University",
            "EM": "Author Email",
            "DI": "DOI",
            "BP": "Begin Page",
            "EP": "End Page",
            "SN": "ISSN",
            "VL": "Volume",
            "ID": "Index Keywords",
            "FU": "Funding Details",
            "FX": "Acknowledgements",
            "JI": "Abbreviated Source Title",
            "OA": "Open Access",
            "IS": "Issue",
            "PMID": "PubMed ID",
        }

        # PATCH 3: data.map(lambda x: x == []) applied the lambda cell-by-cell
        # across the entire DataFrame — on cells containing non-comparable types
        # (int, float) some pandas versions raise TypeError or silently return
        # False instead of True.
        # → replaced with a per-column apply that safely checks for empty lists
        # using isinstance before comparing, avoiding type errors.
        def count_empty_lists(col):
            return col.apply(lambda x: isinstance(x, list) and len(x) == 0).sum()

        missing_counts = (
            data.isna().sum()
            + (data == "").sum()
            + (data == " ").sum()
            + data.apply(count_empty_lists)
        )

        missing_percentage = (missing_counts / total_rows) * 100
        missing_status = get_status(missing_percentage)

        sorted_columns = sorted(
            zip(
                missing_counts.index,
                [column_descriptions.get(col, col) for col in missing_counts.index],
                missing_counts,
                missing_percentage,
                missing_status
            ),
            key=lambda x: x[2]
        )

        fig = create_plotly_table(sorted_columns, dpi)

        table_header = """
        <table style="width:100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 2px solid #dddddd;">
                    <th style="text-align: center; padding: 8px;">Metadata</th>
                    <th style="text-align: center; padding: 8px;">Description</th>
                    <th style="text-align: center; padding: 8px;">Missing Counts</th>
                    <th style="text-align: center; padding: 8px;">Missing %</th>
                    <th style="text-align: center; padding: 8px;">Status</th>
                </tr>
            </thead>
            <tbody>
        """

        table_rows = ""
        for col, description, count, percent, status_z in sorted_columns:
            status_style = get_status_color(status_z)
            table_rows += f"""
            <tr style="border-bottom: 1px solid #dddddd;">
                <td style="text-align: center; padding: 8px;">{col}</td>
                <td style="text-align: center; padding: 8px;">{description}</td>
                <td style="text-align: center; padding: 8px;">{count}</td>
                <td style="text-align: center; padding: 8px;">{percent:.2f}%</td>
                <td style="text-align: center; padding: 8px; {status_style}">{status_z}</td>
            </tr>
            """

        table_footer = "</tbody></table>"
        table_html = table_header + table_rows + table_footer

        if modal:
            m = ui.modal(
                ui.HTML(f"""{table_html}"""),
                title=f"Completeness of bibliographic metadata - {len(data)} documents from {database}",
                easy_close=False,
                footer=ui.div(
                    ui.input_action_button("advice_modal_completeness", "Advice", icon=ICONS["info"], style="background: #5865B9; color: white"),
                    ui.input_action_button("report_modal_completeness", "Report", icon=ICONS["plus"], style="background: #5865B9; color: white"),
                    ui.input_action_button("save_modal_completeness", "Save", icon=ICONS["download"], style="background: #5865B9; color: white"),
                    ui.modal_button("Close", style="background: #5865B9; color: white")
                ),
                size="l"
            )
            ui.modal_show(m)

    if data is not None:
        # PATCH 2: the original code called df.get() a second time inside the
        # return statement — same issue as PATCH 1.
        # → replaced with `data` which is already the copied DataFrame.
        return ui.HTML(
            DT(
                data,
                maxBytes="10MB",
                classes="display compact stripe",
                style="text-transform: uppercase; font-size: small; table-layout: auto;",
                buttons=["pageLength",
                        {"extend": "csvHtml5", "title": f"{database}_Bibliometrix"},
                        {"extend": "excelHtml5", "title": f"{database}_Bibliometrix"}
                ],
                columnDefs=[
                    {
                        "targets": "_all",
                        "createdCell": JavascriptFunction("""
                            function (td, cellData, rowData, row, col) {
                                if (typeof cellData === 'string' && cellData.length > 200) {
                                    const truncatedText = cellData.substring(0, 200) + '...';
                                    $(td).text(truncatedText);
                                    $(td).attr('title', cellData);
                                    $(td).css('overflow', 'hidden');
                                    $(td).css('text-overflow', 'ellipsis');
                                    $(td).css('vertical-align', 'top');
                                } else {
                                    $(td).css('vertical-align', 'top');
                                }
                            }
                        """)
                    }
                ],
                eval_functions=True
            )
        ), table_html, fig
    else:
        return ui.h5("No data available. Please upload a file."), "", None