# MSL PÚ website
Website for firesport league: [Moravskoslezská liga v PÚ](https://www.youtube.com/watch?v=CtEhhjKSOGc&t=3s)


## Project structure
Project is using [Wagtail](https://wagtail.io/) CMS utilizing [Django](https://www.djangoproject.com/) under the hood. Each folder under `/src` represents a different Wagtail app. An app is a self-contained module that provides a specific functionality. Every app has simillar folder structure.

For FE [Bootstrap](https://getbootstrap.com/docs/5.3/getting-started/introduction/) framework is used (CSS and JS) with customizations.

Wagtail (and Django) utilizes [MVT](https://www.geeksforgeeks.org/django-project-mvt-structure/) pattern - therfore division into:
* models - `models.py` = BE database tables
* views - `views.py` files representing user interface (not used much with Wagtail + Bootstrap)
* templates `.html` files under `/templates` folders - static part of FE

## Wagtail apps
Bellow explained from **FE** point of view:
#### /msl_pu_website
Main app (entry point for the website) Contains static files (css, images, js), contains following templates:
* `base.html` - parent template for all other templates, contains head and body for the whole website
* `header.html` - main image and navigation menu
* ...

#### /home
Homepage app - contains following templates:
* `home_page.html` - homepage content

#### /news
News app ("Aktuality")- contains following templates:
* `news_index_page.html` - list of news
* `news_page.html` - single news page

#### /about_msl
About MSL app ("O MSL") - currently no templates

#### /base
Should contain only reusable pieces of code that can be used in any other app - eg. helper functions in `navigation_tags.py`.

#### /search
Search app - currently no use, can be ignored.

## FAQ
### How to get new changes from main branch to my own branch
1. `git checkout main`
2. `git pull`
3. `git checkout my-branch`
4. `git rebase main`
5. `python src/manage.py migrate` (run from the root folder of the project - it is needed only in case of models changes, but its good pracitce to run after every rebase)

### How to run the project
Server can be started in debug mode with VS Code "Run and Debug". It starts the server on [localhost:8000](http://localhost:8000/) Settings for this debug run can be found in `/.vscode/launch.json`.

### Rules for branches naming and commit messages
* For branches use format: `feature/feature-name` or `fix/bug-name` or `chore/what-was-done`
* Commit messages should follow [conventional commits standard](https://www.conventionalcommits.org/en/v1.0.0/):
eg. "feat: add new feature", "fix: fix bug in feature", "chore: update dependencies"

### How to recompile custom-bootstrap.css
Every change in `custom-bootstrap.scss` must me recompiled into `custom-bootstrap.css` - this is included in `base.html`
https://getbootstrap.com/docs/5.3/customize/sass/#compiling
```
sass src/msl_pu_website/static/scss/custom-bootstrap.scss src/msl_pu_website/static/css/custom-bootstrap.css
```
