项目架构：

```
文案库：学习别人怎么写
产品库：知道你到底卖什么
用户库：知道写给谁
策略层：决定这次怎么打
生成层：批量产出
评审层：筛选和修改
合规层：避开风险
反馈层：用发布结果反哺系统
```

技术选型：

```
后端框架：FastAPI
工作流编排：LangGraph
知识库/RAG：LlamaIndex
数据库：PostgreSQL + Milvus
缓存/任务队列：Redis + RQ
对象存储：本地文件
结构化校验：Pydantic
前端：React
观测调试：LangSmith
部署：本地
```

项目目录:

```
app/
  api/
  core/
  db/
  models/
  schemas/
  services/
  workflows/
  rag/
  workers/
  prompts/
frontend/
storage/
docker-compose.yml
```

技术：

```
LLM：文案拆解、标签判断、模板抽象、风险识别
LlamaIndex：批量 ingestion、metadata、embedding、索引、检索
RAG：提供拆解标准、标签体系、few-shot 样例、品牌规则
LangGraph：编排整个拆解和生成流程
PostgreSQL：保存结构化结果
```



流程：

一.文案处理

文案提取 （文案规范化，数据规范化）

文案拆解（元信息）= = = = 模板建立

拆解与模板入库------>**置信度**。

元信息：客观元，主观元

二

未来拓展:加评分、加 A/B 测、加账号风格学习

多轮筛选(人工+agent)

原创性和相似度检查

数据回流：

数据检索，关键词推荐。