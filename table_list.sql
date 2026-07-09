DROP TABLE IF EXISTS sstable;

CREATE TABLE sstable
(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	cliente TEXT NOT NULL,
	telefone INTEGER NOT NULL,
	servico TEXT NOT NULL,
	tecnico TEXT NOT NULL,
	equipamento TEXT NOT NULL
);

INSERT INTO sstable(cliente, telefone, servico, tecnico, equipamento) VALUES
("Ana",  900000000, "Iluminação", "Pedro", "Lâmpada"),
("Ana",  900000000, "Iluminação", "Pedro", "Painel"),
("Ana",  900000000, "Som",        "Luís",  "Microfone"),
("João", 900000001, "Som",        "Pedro", "Microfone"),
("João", 900000001, "Som",        "Pedro", "Altofalante");
