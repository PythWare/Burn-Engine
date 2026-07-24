# Update

Burn Engine will be ready to release soon with many new features for modding Dynasty Warriors 2

# Info
Burn Engine is a high end modding toolkit for Dynasty Warriors 2, meant to replace my Dynasty Warriors 2 tools I made in the past. It's not ready to release but i'll explain the future features. Burn Engine is inspired by Yang Xiao Long from RWBY.

<img width="1913" height="1027" alt="iburn1" src="https://github.com/user-attachments/assets/92431727-3a5b-44dc-a74c-e165b2928365" />

# Afterburn Stageworks (meant to replace Visual Guider as the main Stage Editor to use)

AFterburn Staeworks is Visual Guider overhauled with a new GUI. Panels can be moved around, you can hide the UI, etc. Like with Visual Guider it mods the battlefield data that determines who and where fights for side 1 and 2. Each stage has its map loaded, populated with all squads/forces on the map automatically, allows editing squad data (coordinates where squads spawn, leader id, guard id, parameters, etc), zooming in/out to adjust the display of the map, clicking a squad or their name in the list (which takes you directly to the squad so you don't have to manually find them) displays their squad data, morale bar toggle, guard toggle, etc. Afterburn Stageworks does everything the Visual Guider can but has a way better design and still includes all the features visual guider had even the genetic algorithm. For a full description of what Afterburn Stageworks can do checkout Visual Guider which is what Afterburn Stageworks is based on https://github.com/PythWare/Dynasty-Warriors-2-Visual-Guider

<img width="1920" height="1046" alt="b2" src="https://github.com/user-attachments/assets/b69820c6-d35c-43b9-ae7f-6bcb2b3948ee" />

<img width="1917" height="1041" alt="b3" src="https://github.com/user-attachments/assets/2365d877-2612-4d6c-be90-787090b31830" />

# Knuckleforge (unit editor)

This handles modding unit data which for DW2 involves name, model, motion/moveset, horse, color (uniform), etc.

<img width="1920" height="1038" alt="b4" src="https://github.com/user-attachments/assets/1fadc48f-04ee-4bca-b248-617401e5d325" />

# Ember Registry (string editor for unit names)

Handles modding the string names for units. This helps with having custom units made so that their name can be custom too.

<img width="1920" height="1036" alt="b6" src="https://github.com/user-attachments/assets/bbc5847b-8051-4879-b430-1fb4ceb0a46d" />

# Golden Lineage (bodyguard editor)

This tool handles modding player bodyguards. Ever noticed how player bodyguards can only ever have sword movesets no matter how much they progress for ranks/class? With Bodyguard Forge you can mod how your bodyguards' progress. That means you can have bodyguards with different movesets (sword, spear, pike glaive, etc), models, etc. Image 12 is an example of a mod made by Bodyguard Forge.

<img width="1920" height="1034" alt="b7" src="https://github.com/user-attachments/assets/88d8580a-a33e-4419-b82b-2f2837dd44e3" />

# Dragonvault (item editor)

Handles modding the item data.

<img width="1917" height="1037" alt="b5" src="https://github.com/user-attachments/assets/805af078-08f7-4eec-9bf0-aead1fc63f42" />

# Emberchain

Handles ATK data, attack properties.

<img width="1915" height="1038" alt="emb3" src="https://github.com/user-attachments/assets/69118e7e-7ddb-4cbf-9a65-32548d2241f9" />

# Emberflow

Handles MOV data, properties for moveset animations.

<img width="1917" height="1036" alt="emb7" src="https://github.com/user-attachments/assets/a44df5ae-ae0b-4136-b721-3a33dd568383" />

# Overdrive Motionworks

A 3D moveset editor that renders models and animates it based on the MOT files (moveset animations), it's in the early stage but it renders all moveset animations and will soon support creating custom movesets

<img width="1907" height="1039" alt="ov1" src="https://github.com/user-attachments/assets/06d65a67-15e4-4e43-adb0-250dc4f223c1" />

<img width="1911" height="1026" alt="ov3" src="https://github.com/user-attachments/assets/a8cbb010-f2b5-45c3-9663-0a1ee13e7115" />

<img width="1894" height="1035" alt="ov6" src="https://github.com/user-attachments/assets/e3e57150-bf3d-4e88-aa3c-72249d9e82a8" />

# Celica Mapworks, 3D Map Editor

This is very different from Afterburn Stageworks. Stage Data (what the Stage Editor mods) involves what is basically battlefield data, like who fights on the stage. The Map Editor will mod the literal maps. That'll include objects on the map (gates, walls, castles, boxes, towers, flags, breakable boxes/vases, etc), collision data so objects have proper physics, terrain data (the terrain itself such as hills, land, etc), pathfinding data, and other things. The end result will be allowing you to create entirely custom and new maps. This is a work in progress but it has been tested by me and i've even made videos of playing on a custom Hu Lao Gate map where I moved one of where the gates is actually located. The videos showing this are in the musou warriors discord server.

Main Hub

<img width="1203" height="726" alt="gui1" src="https://github.com/user-attachments/assets/6cdda9e5-ec9e-4036-bc5f-bcecc1ee6227" />

Images show examples of maps being rendered.
<img width="1586" height="841" alt="guandu1" src="https://github.com/user-attachments/assets/77ed5acf-0f26-41a6-a911-6486ead7c9fc" />
<img width="1895" height="882" alt="guandu2" src="https://github.com/user-attachments/assets/2d6a1989-d83d-46a0-8dd9-3985afb07e61" />
<img width="1671" height="785" alt="guandu4" src="https://github.com/user-attachments/assets/5d071041-454c-4c16-9c99-d5c5f7605a25" />
<img width="1903" height="814" alt="ytrt1" src="https://github.com/user-attachments/assets/0a1a5a60-4134-48ba-90af-b442e235ce53" />
<img width="1920" height="1040" alt="celic12" src="https://github.com/user-attachments/assets/1d5ad7f6-6e37-4745-b69e-87f89d03aca3" />

Images show examples of pathfinding data rendered and moddable

<img width="1905" height="1028" alt="cm9" src="https://github.com/user-attachments/assets/316638a3-0954-4e42-8bf5-6fb3223d5755" />

<img width="1919" height="1029" alt="cm3" src="https://github.com/user-attachments/assets/a04af13e-25fc-40bb-8dd2-0ce71864026d" />

<img width="1917" height="1034" alt="cm1" src="https://github.com/user-attachments/assets/8be766e9-a87c-4eac-970d-84ce604aedc3" />

<img width="1898" height="1028" alt="cm7" src="https://github.com/user-attachments/assets/4199f9d3-bd25-49d2-abbe-1f4a6a295a4e" />

Ingame examples (shows a Gate positioned further north while the other shows the breakable boxes/vases that originally start near one of the respawn gates near Yuan Shao being placed near a tree further south.)

<img width="1267" height="724" alt="map2" src="https://github.com/user-attachments/assets/26df4697-404c-4495-8b21-341001cb087b" />
<img width="1277" height="720" alt="ts8" src="https://github.com/user-attachments/assets/3754b6b2-4e95-48d1-9cc8-b178683a2e36" />

Image examples of Yang Xiao Long playable in DW2 (I will be giving her a custom brawler moveset later on)

<img width="1295" height="909" alt="ov8" src="https://github.com/user-attachments/assets/7e4264d1-3da9-4d0d-8bb8-7d829ee471ed" />

<img width="1358" height="1010" alt="ov10" src="https://github.com/user-attachments/assets/8161a1c5-d4c5-493d-8193-3d8e1bb4a3ff" />

<img width="1359" height="1018" alt="ov11" src="https://github.com/user-attachments/assets/24189b2c-27b5-461f-9823-14eb5c6df7b8" />

# Credits

Credit goes to Michael, Passion Wagon, Aurvi, and The Tempest for documentation with Stage/Morale Data. Credit also goes to Michael for documentation on model, motion/moveset, and color values. Michael gave permission for me to include his lists of documentation in Visual Guider so credit goes to him for the model, motion/moveset, and army color values/strings. Further credit also goes to Michael for discovering the data that determines if player bodyguards follow like AI guards. 

I only take credit for the code/design of Burn Engine, Celica Mapworks, and any other modding software I make but also the understanding of map formats (gob, cob, ob2, etc for maps).

# Future Plans

I hope to make an Event Editor, this would allow custom events to be made and open a lot of potential for scripting possibly. There are other tools indevelopment for DW2 modding during my free time but my biggest focus is getting the map editor finished. 
