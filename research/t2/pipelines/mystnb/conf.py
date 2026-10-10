project = "T2 MyST-NB"
language = "ru"
extensions = ["myst_nb"]
# Исполнять ноутбуки при сборке и кэшировать результат по хешу кода ячеек (jupyter-cache)
nb_execution_mode = "cache"
nb_execution_cache_path = ".jupyter_cache"
nb_execution_timeout = 600
nb_execution_raise_on_error = True
html_theme = "alabaster"
exclude_patterns = ["_build", ".jupyter_cache"]
