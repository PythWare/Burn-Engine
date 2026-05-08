# Info
Real Steel is a high end modding toolkit for Dynasty Warriors 2, meant to replace my Dynasty Warriors 2 tools I made in the past (the 2.0 versions). It's not ready to release but i'll explain the future features. Real Steel is inspired by Tetsutetsu from My hero Academia.

<img width="1280" height="1007" alt="ts10" src="https://github.com/user-attachments/assets/3e68e32b-cc0e-44fa-810c-05c9d5e6c367" />

# Steel Guider (meant to replace Visual Guider as the main Stage Editor to use)

The Steel Guider is Visual Guider overhauled with a new GUI. Panels can be moved around, you can hide the UI, etc. Like with Visual Guider it mods the battlefield data that determines who and where fights for side 1 and 2. Each stage has its map loaded, populated with all squads/forces on the map automatically, allows editing squad data (coordinates where squads spawn, leader id, guard id, parameters, etc), zooming in/out to adjust the display of the map, clicking a squad or their name in the list (which takes you directly to the squad so you don't have to manually find them) displays their squad data, morale bar toggle, guard toggle, etc. The Steel Guider does everything the Visual Guider can but has a way better design and still includes all the features visual guider had even the genetic algorithm. For a full description of what Steel Guider can do checkout Visual Guider which is what Steel Guider is based on https://github.com/PythWare/Dynasty-Warriors-2-Visual-Guider

<img width="1908" height="1029" alt="ts2" src="https://github.com/user-attachments/assets/cb6d327e-ee44-4384-bf03-b9b2e885a815" />
<img width="1914" height="1030" alt="ts3" src="https://github.com/user-attachments/assets/a8796542-c465-4e36-acd7-2b78f4e7d486" />


# Unit Forge (unit editor)

This handles modding unit data which for DW2 involves name, model, motion/moveset, horse, color (uniform), etc. A new feature is Preview Image support, now you can see preview images of different units to help visually see what each color looks like for most models.

<img width="1497" height="983" alt="ts4" src="https://github.com/user-attachments/assets/4de9b76c-e7b6-4e82-91b9-ca49a562abb4" />
<img width="1501" height="982" alt="ts5" src="https://github.com/user-attachments/assets/c7c36c20-129d-416e-a35c-64a64be26bff" />

# Name Forge (string editor for unit names)

Handles modding the string names for units. This helps with having custom units made so that their name can be custom too.

<img width="898" height="850" alt="ts6" src="https://github.com/user-attachments/assets/9212e99a-4e28-4a60-9a93-24a82df14a0c" />


# Bodyguard Forge

This tool handles modding player bodyguards. Ever noticed how player bodyguards can only ever have sword movesets no matter how much they progress for ranks/class? With Bodyguard Forge you can mod how your bodyguards' progress. That means you can have bodyguards with different movesets (sword, spear, pike glaive, etc), models, etc. Image 12 is an example of a mod made by Bodyguard Forge.

<img width="1361" height="966" alt="ts7" src="https://github.com/user-attachments/assets/f06813d3-3f57-476a-83cd-aa75a7f08c8e" />

# Item Calibration Bay

Handles modding the item data.

<img width="1517" height="847" alt="ts11" src="https://github.com/user-attachments/assets/2819040f-fc6a-465f-a29b-dcf98e9a80cf" />

# Everlasting Steel, 3D Map Editor

This is very different from Steel Guider. Stage Data (what the Stage Editor mods) involves what is basically battlefield data, like who fights on the stage. The Map Editor will mod the literal maps. That'll include objects on the map (gates, walls, castles, boxes, towers, flags, breakable boxes/vases, etc), collision data so objects have proper physics, terrain data (the terrain itself such as hills, land, etc), and other things. The end result will be allowing you to create entirely custom and new maps. This is a work in progress but it has been tested by me and i've even made videos of playing on a custom Hu Lao Gate map where I moved where Si Shui Gate is actually located. The videos showing this are in the musou warriors discord server.

Map Editor is going to be redesigned with a Steel theme but i included a sneak peak image of what the prototype looks like. Images show examples of modding the map, one shows Si Shui Gate positioned further north while the other shows the breakable boxes/vases that originally start near one of the respawn gates near Yuan Shao being placed near a tree further south.

<img width="1428" height="896" alt="28" src="https://github.com/user-attachments/assets/7ba36212-6ea8-4f52-893c-fc8680d14584" />
<img width="1432" height="898" alt="29" src="https://github.com/user-attachments/assets/2eb3b966-e146-4f59-b451-7c5b18c43bce" />
<img width="1452" height="902" alt="31" src="https://github.com/user-attachments/assets/b5e0b2b7-73da-43f4-a33a-5267a5801d4a" />
<img width="1802" height="741" alt="38" src="https://github.com/user-attachments/assets/5cc790f8-eda1-4aa6-9d23-b4511295862f" />
<img width="1267" height="724" alt="map2" src="https://github.com/user-attachments/assets/26df4697-404c-4495-8b21-341001cb087b" />
<img width="1277" height="720" alt="ts8" src="https://github.com/user-attachments/assets/3754b6b2-4e95-48d1-9cc8-b178683a2e36" />

# Credits

Credit goes to Michael, Passion Wagon, Aurvi, and The Tempest for documentation with Stage/Morale Data. Credit also goes to Michael for documentation on model, motion/moveset, and color values. Michael gave permission for me to include his lists of documentation in Visual Guider so credit goes to him for the model, motion/moveset, and army color values/strings. Further credit also goes to Michael for discovering the data that determines if player bodyguards follow like AI guards. 

I only take credit for the code/design of Real Steel and also the understanding of map formats (gob, cob, ob2, etc for maps).

# Future Plans

I hope to make an Event Editor, this would allow custom events to be made and open a lot of potential for scripting possibly. There are other tools indevelopment for DW2 modding during my free time but my biggest focus is getting the map editor finished. 
