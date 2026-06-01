# 📊 ECharts 图表详解

>i **在编辑器中输入 ```echarts 代码块。每个图表展示美化写法和渲染效果。**

## 1. 柱状图

**使用方式：用 ```echarts 包裹**

```json
{
  "title": {"text": "季度销售", "left": "center"},
  "xAxis": {"type":"category","data":["Q1","Q2","Q3","Q4"]},
  "yAxis": {"type": "value"},
  "series": [{"type":"bar","data":[120,200,150,80]}]
}
```

**渲染效果：**

```echarts
{"title":{"text":"季度销售","left":"center"},"xAxis":{"type":"category","data":["Q1","Q2","Q3","Q4"]},"yAxis":{"type":"value"},"series":[{"type":"bar","data":[120,200,150,80]}]}
```

## 2. 折线图

**使用方式：用 ```echarts 包裹**

```json
{
  "title": {"text": "周访问量", "left": "center"},
  "tooltip": {"trigger": "axis"},
  "xAxis": {"type":"category","data":["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]},
  "yAxis": {"type": "value"},
  "series": [{"type":"line","data":[150,230,224,218,135,147,260],"smooth":true}]
}
```

**渲染效果：**

```echarts
{"title":{"text":"周访问量","left":"center"},"tooltip":{"trigger":"axis"},"xAxis":{"type":"category","data":["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]},"yAxis":{"type":"value"},"series":[{"type":"line","data":[150,230,224,218,135,147,260],"smooth":true}]}
```

## 3. 饼图

**使用方式：用 ```echarts 包裹**

```json
{
  "title": {"text": "流量来源", "left": "center"},
  "series": [{"type":"pie","radius":"60%","data":[
    {"value":335,"name":"直接"},{"value":310,"name":"邮件"},
    {"value":234,"name":"广告"},{"value":135,"name":"视频"},
    {"value":548,"name":"搜索"}
  ]}]
}
```

**渲染效果：**

```echarts
{"title":{"text":"流量来源","left":"center"},"series":[{"type":"pie","radius":"60%","data":[{"value":335,"name":"直接"},{"value":310,"name":"邮件"},{"value":234,"name":"广告"},{"value":135,"name":"视频"},{"value":548,"name":"搜索"}]}]}
```

## 4. 散点图

**使用方式：用 ```echarts 包裹**

```json
{
  "title": {"text": "身高体重分布", "left": "center"},
  "xAxis": {"type":"value","name":"身高(cm)"},
  "yAxis": {"type":"value","name":"体重(kg)"},
  "series": [{"type":"scatter","data":[[161,51],[167,62],[171,65],[175,70],[180,80],[158,48],[163,55]]}]
}
```

**渲染效果：**

```echarts
{"title":{"text":"身高体重分布","left":"center"},"xAxis":{"type":"value","name":"身高(cm)"},"yAxis":{"type":"value","name":"体重(kg)"},"series":[{"type":"scatter","data":[[161,51],[167,62],[171,65],[175,70],[180,80],[158,48],[163,55]]}]}
```

## 5. 雷达图

**使用方式：用 ```echarts 包裹**

```json
{
  "title": {"text": "能力评估", "left": "center"},
  "radar": {"indicator":[
    {"name":"技术","max":100},{"name":"沟通","max":100},
    {"name":"管理","max":100},{"name":"创新","max":100},
    {"name":"执行","max":100}
  ]},
  "series": [{"type":"radar","data":[{"value":[85,70,90,65,80],"name":"员工A"}]}]
}
```

**渲染效果：**

```echarts
{"title":{"text":"能力评估","left":"center"},"radar":{"indicator":[{"name":"技术","max":100},{"name":"沟通","max":100},{"name":"管理","max":100},{"name":"创新","max":100},{"name":"执行","max":100}]},"series":[{"type":"radar","data":[{"value":[85,70,90,65,80],"name":"员工A"}]}]}
```

>w JSON 必须使用双引号，最后一项后不能有逗号。使用方式中的格式化 JSON 便于阅读，工具栏"图表"按钮自动生成渲染所需格式。
