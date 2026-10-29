# Amazon Berkeley Objects (c) by Amazon.com

[Amazon Berkeley Objects](https://amazon-berkeley-objects.s3.us-east-1.amazonaws.com/index.html)
is a collection of product listings with multilingual metadata, catalog
imagery, high-quality 3d models with materials and parts, and benchmarks derived
from that data.

## License

This work is licensed under the Creative Commons Attribution 4.0 International
Public License. To obtain a copy of the full license, see LICENSE-CC-BY-4.0.txt,
visit [CreativeCommons.org](https://creativecommons.org/licenses/by/4.0/)
or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

Under the following terms:

  * Attribution — You must give appropriate credit, provide a link to the
    license, and indicate if changes were made. You may do so in any reasonable
    manner, but not in any way that suggests the licensor endorses you or your
    use.

  * No additional restrictions — You may not apply legal terms or technological
    measures that legally restrict others from doing anything the license
    permits.

## Attribution

Credit for the data, including all images and 3d models, must be given to:

> Amazon.com

Credit for building the dataset, archives and benchmark sets must be given to:

> Matthieu Guillaumin (Amazon.com), Thomas Dideriksen (Amazon.com),
> Kenan Deng (Amazon.com), Himanshu Arora (Amazon.com),
> Jasmine Collins (UC Berkeley) and Jitendra Malik (UC Berkeley)

## Description

The `3dmodels/` directory and `abo-3dmodels.tar` archives are made of the
following files:

  * `LICENSE-CC-BY-4.0.txt` - The License file. You must read, agree and
    comply to the License before using the Amazon Berkeley Objects data.

  * `3dmodels/metadata/3dmodels.csv.gz` - 3d model metadata. This file is a
    gzip-compressed comma-separated value (CSV) file with the following fields:
    `3dmodel_id`, `path`, `meshes`, `materials`, `textures`, `images`,
    `image_height_max`, `image_height_min`, `image_width_max`,
    `image_width_min`, `vertices`, `faces`, `extent_x`, `extent_y`, `extent_z`.

    - `3dmodel_id`: Reference for the 3d model, as provided in the `3dmodel_id`
      field of the listings metadata
    - `path`: Location of the 3d model, relative to `3dmodels/original/`
    - `meshes`: Number of meshes in the geometry
    - `materials`: Number of materials in the 3d model
    - `textures`: Number of textures in the 3d model
    - `images`: Number of image resources in the 3d model
    - `image_{heigh,width}_{min,max}`: Minimal and maximal dimensions of the
      image resources in the 3d model
    - `vertices`: Number of vertices in the geometry
    - `faces`: Number of faces in the geometry
    - `extent_{x,y,z}`: Extent of the geometry in each dimension

    Below are are first 10 lines of `3dmodels/metadata/3dmodels.csv.gz`:
```
3dmodel_id,path,meshes,materials,textures,images,image_height_max,image_height_min,image_width_max,image_width_min,vertices,faces,extent_x,extent_y,extent_z
B01N2PLWIL,L/B01N2PLWIL.glb,1,1,3,3,4096,4096,4096,4096,10990,14380,0.571499943733216,0.11684001048680606,0.07111982014177629
B075QFCHM9,9/B075QFCHM9.glb,1,1,3,3,2048,2048,2048,2048,11973,19568,1.840071976184845,1.0669103860855103,2.3675915002822876
B07H469871,1/B07H469871.glb,1,1,3,3,4096,4096,4096,4096,1602,1950,1.1113524436950684,1.3880813121795654,0.39794909954071045
B07H8V49M2,2/B07H8V49M2.glb,1,1,3,3,4096,4096,4096,4096,3760,5710,1.4998703368605968,2.11988401412964,0.5897879977087402
B07DBHPK4G,G/B07DBHPK4G.glb,1,1,3,3,4096,4096,4096,4096,13704,22736,0.37921489775180817,1.6228150129318237,0.37921497225761414
B0842LM2DN,N/B0842LM2DN.glb,1,1,3,3,4096,4096,4096,4096,4078,7584,0.22779017686843872,0.2348586767911911,0.22779015451669693
B07HK6B4D7,7/B07HK6B4D7.glb,1,1,4,4,2048,2048,2048,2048,12221,19268,0.1887289583683014,0.6650936603546143,0.421692430973053
B07B4FZN9H,H/B07B4FZN9H.glb,1,1,3,3,2048,2048,2048,2048,13595,22644,3.3838289976119995,0.9963648915290833,2.048073887825012
B07B4Z9BS4,4/B07B4Z9BS4.glb,1,1,4,4,2048,2048,2048,2048,9259,16178,0.2793540060520172,0.2693932056427002,0.2793540358543396
```

  * `3dmodels/original/<path>` - 3d model files. The 3d models are provided in
    the [glTF-2.0 format](
    https://github.com/KhronosGroup/glTF/blob/master/specification/2.0/README.md
    ) (GLB/binary representation). All models adhere to the following
    conventions:
    1. Positive `Y` direction is up.
    2. Positive `Z` direction is pointing to the *natural* front-side of the
       product, wherever applicable.
    3. Products that are designed to stand on a surface (i.e. a floor) are
       centered on the origin, but translated up (towards positive `Y`) such
       that they *stand* on the `Y=0` plane.
    4. Products that are designed to hang from a surface (i.e. a ceiling) are
       centered on the origin, but translated down (towards negative `Y`) such
       that they *hang* from the `Y=0` plane.
    5. Products that are designed to hang on a wall are centered on the origin,
       but translated forward (towards positive `Z`) such that their backside
       aligns with the `Z=0` plane.
