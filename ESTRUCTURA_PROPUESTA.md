# Estructura propuesta

## Archivos a eliminar (duplicados exactos)
- QNodes/src/constants/base.py → usar GeoMIP/src/constants/base.py
- QNodes/src/funcs/iit.py → funciones equivalentes en GeoMIP/src/funcs/base.py
- QNodes/src/funcs/format.py → equivalente en GeoMIP/src/funcs/format.py
- QNodes/src/models/core/ncube.py → idéntico a GeoMIP/src/models/core/ncube.py
- QNodes/src/models/core/system.py → idéntico a GeoMIP/src/models/core/system.py

## Archivos a fusionar
- GeoMIP/src/models/core/ncube.py + system.py → un solo core/system.py
  (NCube nunca se usa fuera de System)

## Nueva estructura sugerida
geomip/
├── core/
│   ├── system.py      (System + NCube fusionados)
│   └── metrics.py     (emd_efecto, emd_causal, hamming)
├── strategies/
│   ├── base.py        (SIA abstracto)
│   ├── geometric.py
│   ├── q_nodes.py
│   └── force.py
├── utils/
│   ├── format.py
│   └── io.py          (manager + lectura excel)
└── exec.py
