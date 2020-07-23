--TODO find better names for all this crap and refactor the python
--TODO deletion cascading and whatnot
--todo i need to find an actually helpful syntax checker

--create table if not exists sheet (
--  id INTEGER PRIMARY KEY AUTOINCREMENT -- .SH###- 3 digits zero padded
--  ); -- sqlite3.OperationalError: AUTOINCREMENT not allowed on WITHOUT ROWID tables


create table if not exists sheettype (
  id integer primary key autoincrement,
  type TEXT NOT NULL,
  --FOREIGN KEY(id) REFERENCES sheet(id),
  FOREIGN KEY(type) REFERENCES sheetspecs(name)
  ); -- sqlite3.OperationalError: AUTOINCREMENT not allowed on WITHOUT ROWID tables

create table if not exists sheetusage (
  id INTEGER,
  used_idx INTEGER NOT NULL,
  FOREIGN KEY(id) REFERENCES sheettype(id),
  PRIMARY KEY(id, used_idx)
  ) WITHOUT ROWID;

--todo move to sep file
create table if not exists promptstate (
  prompt_session integer primary key,
  last_sheetid integer,
--  foreign key (last_sheetid) references sheettype (id),-- makes deleting sheets problematic so...dont delete sheets? 
  foreign key (last_sheetid) references sheettype (id)
  ) without rowid;

create table if not exists labels (
  id integer primary key --todo i always forget how to do the get next values thing
  )
