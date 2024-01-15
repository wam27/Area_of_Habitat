# Area of Habitat
 ## Protocol to map AOH with python
 ## Area of Habitat maps the habitat (elevation and tree cover) within a species range. Here, I provide the python code to map AOHs of birds using eBird and GBIF data.

Protocol for mapping Area of Habita (AOH).
This is the fourth step in the protocol used for mapping 1000 AOHs for birds in the Americas.
The published paper can be found in the following link: https://doi.org/10.1371/journal.pone.0259299
In short, this tool takes presence points, extracts elevation and forest values, and overlaps elevation and habitat within the species distribution, resulting in the AOH. See more info on what AOHs are, here: https://doi.org/10.1016/j.tree.2019.06.009
The user needs to have an ArcGIS account in order to use arcpy packages to set absences. If AOH only is required, the user do not need to install arcpy. I am working on replacing arcpy with other packages to reduce dependency on ArcGIS.

