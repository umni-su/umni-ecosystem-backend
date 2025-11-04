## This is a plugin template

### Localization (l10n)

```bash

#1) Move to l10n plugin directory
cd plugins/custom/{plugin_name}/l10n

#2) Sure that plugins/custom/{plugin_name}/l10n/templates directory exists
pybabel extract -o ./templates/messages.pot ../

#3) Add your langs 
pybabel init -i ./templates/messages.pot -d l10n -l en

# 4) Compile
pybabel init -i ./templates/messages.pot -d l10n -l en
```

#### Update translations

```bash

#1) Move to l10n plugin directory
cd plugins/custom/{plugin_name}/l10n

#2) Update
pybabel update -i ./templates/messages.pot -d .

#3) Compile
pybabel init -i ./templates/messages.pot -d l10n -l en
```