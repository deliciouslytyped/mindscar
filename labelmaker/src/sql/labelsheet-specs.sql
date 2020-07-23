--a4 = (210, 297)
--grid = (4, 16)
--label_dim = (48.3, 16.9)

create table if not exists sheetspecs (
  name TEXT PRIMARY KEY,
  label_width FLOAT NOT NULL,
  label_height FLOAT NOT NULL,
  columns INTEGER NOT NULL,
  rows INTEGER NOT NULL,
  sheet_width FLOAT NOT NULL,
  sheet_height FLOAT NOT NULL,
  left_margin FLOAT NOT NULL,
  top_margin FLOAT NOT NULL,
  row_gap FLOAT NOT NULL,
  column_gap FLOAT NOT NULL
  ) WITHOUT ROWID
