drop table if exists users;
create table users (
  id integer primary key autoincrement,
  email text not null unique,
  language text not null
);