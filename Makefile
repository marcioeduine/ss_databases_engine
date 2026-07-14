# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    Makefile                                          :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 09:38:11 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/09 09:56:46 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #

NAME		= ssdatabases_cli
DB			= database.db
SQL			= sqlite3
SQLFLAGS	= -column -header
PY_MAIN		= src/cli.py
SRC			= table_list.sql

all: $(DB)

$(DB): $(SRC)
	$(SQL) $(SQLFLAGS) $(DB) < $(SRC)

clean:
	rm -rf ./build ./dist ./$(NAME).spec

fclean: clean
	rm -f $(DB)

re: fclean all

run: $(SRC) $(DB)
	@$(PY_MAIN) $(DB)

build:
	pyinstaller --onefile --name=$(NAME) $(PY_MAIN)

.PHONY: all fclean re run
