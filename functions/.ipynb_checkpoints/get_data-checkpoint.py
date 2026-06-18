from www.services import *


def get_data(input, database, df, reset_callback=None):
    """
    Handle the data upload and display process.
    
    Args:
        input: An object that provides user input methods.
        database: The name of the database.
        df: A DataFrame object to store the data.
        reset_callback: Function to call to reset analysis results (optional)
        
    Returns:
        A message indicating the status of the data upload.
    """
    file: list[FileInfo] | None = input.Dataset()
    
    if file is None:
        text = ui.h5("Please select a file to begin importing your data.")

    elif input.select() == "1A":
        ui.update_action_button("action_button_save", disabled=False)
        
        source = input.database()
        author = input.author()
        
        try:
            # Check if multiple files are selected
            if len(file) > 1:
                # Process multiple files
                json = process_multiple_files(file, source, author)
                df.set(pd.read_json(StringIO(json)))
                # Reset all analysis results when new dataset is loaded
                if reset_callback:
                    reset_callback()
                text = ui.p(
                    f"{database}'s files uploaded and processed successfully! "
                    f"{len(file)} files have been processed and combined. "
                    f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                )
            else:
                # Process single file (original logic)
                type = file[0]["name"]
                json = biblio_json(file[0]["datapath"], source, type, author)
                df.set(pd.read_json(StringIO(json)))
                # Reset all analysis results when new dataset is loaded
                if reset_callback:
                    reset_callback()
                
                if type.endswith(".zip"):
                    text = ui.p(
                        f"{database}'s ZIP archive uploaded and extracted successfully! "
                        f"Multiple files have been processed and combined. "
                        f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                    )
                else:
                    text = ui.p(
                        f"{database}'s file uploaded successfully! You can now proceed to analyze your data. "
                        f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                    )
        except Exception as e:
            text = ui.div(
                ui.h5("Error processing file(s):", style="color: red;"),
                ui.p(str(e), style="color: red;"),
                ui.p("Please check that your files are in the correct format and try again.", style="color: gray;")
            )

    elif input.select() == "1B":
        # PATCH: support both CSV and Excel formats
        fpath = file[0]["datapath"]
        fname = file[0]["name"]
        if fname.endswith(".csv"):
            loaded_df = pd.read_csv(fpath)
        else:
            loaded_df = pd.read_excel(fpath)
    
        # PATCH: deserialize list columns from string representation back to actual lists.
        # When a DataFrame with list columns is saved to CSV, pandas serializes lists as
        # strings (e.g. "['a', 'b']"). On reload they must be converted back to real lists
        # otherwise all author/keyword/citation analyses produce empty results.
        list_cols = ['AU', 'AF', 'C1', 'AU_CO', 'DE', 'ID', 'CR']
        for col in list_cols:
            if col in loaded_df.columns:
                loaded_df[col] = loaded_df[col].apply(
                    lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else (x if isinstance(x, list) else [])
                )
    
        df.set(loaded_df)
        if reset_callback:
            reset_callback()
        text = ui.p(
            f"{database}'s file uploaded successfully! You can now proceed to analyze your data. "
            f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
        )

    else:
        text = ""

    return text
