# 3. Mapping IFC Entities to Brick Classes
## STEP 1 — IFC → BOT Basic Spatial Mapping
まずは以下の４つの空間エンティティの対応関係を確定する
→ この4つは IFC の建物空間階層の中核であり, IFC 文書にも「空間構造を構成する基本要素」であると明記されている
→ 同様に，BOT でも bot:Site, bot:Building, bot:Storey, bot:Space が明確に定義されている（コアトポロジ概念）

| IFC Entity | BOT Class | Mapping Type | 根拠 |
| ---- | ---- | ---- | ---- |
| IfcSite | bot:Site | 1:1 | BOT公式仕様に Site が Zone のサブクラスとして定義 |
| IfcBuilding | bot:Building | 1:1 | 建物トポロジの階層として Building が定義 |
| IfcBuildingStorey | bot:Storey | 1:1 | IFC で Storey は空間階層要素として定義される/ BOT に対応する Storey が存在 |
| IfcSpace | bot:Space | 1:1 | IFC Space は階層的空間構造の一部である / BOT に Space が存在 |

この4つの空間エンティティはIfcRelAggregatesによって，その階層構造が表現される．
BOT では bot:containsZoneもしくはそのサブプロパティ:

・bot:hasBuilding

・bot:hasStorey

・bot:hasSpace

によって定義される．

| IFC Entity | BOT Class | Mapping Type |
| ---- | ---- | ---- |
| IFC.IfcRelAggregates | BOT.bot:containsZone/bot:hasBuilding/bot:hasStorey/bot:hasSpace| 1:N |


## STEP 2 — BOT ↔ Brick Alignment Basic Spatial Mapping
「BRICKAlignment.ttl」を最優先根拠にする
W3C LBD CG の BOT リポジトリには BRICKAlignment.ttl が含まれており，
「BOT v0.3.2 と Brick v1.1.1 の対応関係」が正式に定義されている(必要であれば，Brick v1.4.0に定義変更)

## STEP 3 — IFC → Brick Equipment / Point Mapping
設備 (Equipment) のマッピングを機器カテゴリ別に定義する

IfcAirTerminal → Brick:VAV や diffusers
IfcFan → Brick:Fan
IfcCoil → Brick:Heating_Coil / Cooling_Coil
IfcUnitaryEquipment → Brick:AHU

## 3.1 Creating mapping table for entities that can be mapped one-to-one

## 3.2 Identifying IFC entities that do not directly correspond to Brick


1対1マッピング
特定のIFCエンティティ(例 IfcSpace IfcDoor)は Brick の単一クラス(例 brick:Space brick:Door)に直接対応する
この場合 Brick は 空間階層や静的要素を表現するための語彙であり, IFC 側の階層構造や GUID をそのまま継承することで双方向参照が可能となる

1対1は主に以下で成立する

空間モデル(IfcSite IfcBuilding IfcBuildingStorey IfcSpace)
静的建築要素(IfcWall IfcDoor IfcWindow)
明確に定義された機器(IfcBoiler IfcChiller など)

1対多マッピング
逆に多くの設備要素や論理的関係は 1対多 となる
例として IfcSensor 1つから以下が生成され得る

brick:Temperature_Sensor
brick:Point (複数)
brick:hasPoint 関係 (設備と点の接続)
brick:feeds 関係 (空間やゾーンとの論理関係)

IFC は 形状と物理設備中心
Brick は センサー データポイント 制御関係中心
ゆえに Brick グラフの方が粒度が高く,
1つの IFC 要素 ⇒ 複数の Brick オブジェクト
という構造が基本となる

2. bDNS と bSDD がどのように作用するか
ここからが本質問の核心である
両者は IFC と Brick の中間に位置する語彙・命名規則の補完レイヤとして作用する