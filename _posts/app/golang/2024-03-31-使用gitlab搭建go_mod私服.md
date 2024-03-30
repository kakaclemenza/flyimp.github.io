---
layout: post
title: 使用gitlab搭建go_mod私服
category: app
typora-root-url: ../../..
---

## 背景

公司私有的gitlab，需要共享一些基础库代码，就会用到go mod私服。这里记录下go mod私服的使用过程。

## 过程

1. 设置私有库：
   设置私有库后，go会自动设置GONOPROXY，GONOSUMDB两个环境变量，表示私有库不走代理，也不检查代码sum。

   ```sh
   go env -w GOPRIVATE="*.company.io,*.company.com" 
   ```

2. 如果要更新不支持https协议的私有库，还需再做如下的配置。

   * `go get -insecure`，但是很麻烦，每个包都需要手动在go mod下导入（go mod自己是不支持HTTP的，这么做是合理的）；
   * `go env -w GOINSECURE=private.repo.com`，设置`GOINSECURE`参数，非常方便。仅在`go 1.14`后新加入。



## gitlab私有库维护规范

> ref: 
>
> * https://www.modb.pro/db/485947
> * https://zhuanlan.zhihu.com/p/584834288

私有库允许成员提交代码并不断完善，提交规范与github上一致，主库不允许直接提交，只允许提PR，并由库管理员审核然后合并进主库（在github界面 “Branch protection rules”（分支保护规则）部分配置的）。

* 首先fork一份主库代码到自己账号下
* 本地clone自己账号下的派生项目
* 创建并切换到本地新分支，分支的命名尽量简洁，并与解决的问题相关：
  git checkout -b feat-xxx
* 在分支上做修改，提交并push到派生项目
* 提交PR准备：提交 PR 之前，可能有新的提交和 PR 被合并到原项目，需要先更新
* 更新完，在github网页上点击“Contribute”按钮来开启一个 PR，或者直接点 Issues 边上的 Pull requests 进入对应页面。
  * 按每个开源项目的Contribute说明填写标题、描述
  * 点击右下角“Create pull request”就完成了一个 PR 的创建了
* Reviewers意见修复：在 review 开始之前，合并多个 commits 记录为一个；在 review 开始之后，针对 reviewers 的修改意见所产生的新 commit，不向前合并。review意见的修复，直接在本地对应分支提交，即可自动追加到PR中。



git易用错指令：

* rebase：变基。如指令名字所示，本质上是将当前分支的基地址对齐到目标分支。
  **rebase黄金法则**：永远不要在公共共享分支上rebase！！！不然会导致提交历史轨迹交叉混乱。所以rebase主要是在规范的PR中，**在个人克隆库中使用**！
  常见用法：

  * 更新远程分支内容，替代`git pull = git fetch + git merge`：

    ```sh
    #更新远程分支到本地关联分支
    git checkout master
    #git pull --rebase origin/master
    git pull --rebase
    ```

  * 将本地master分支内容同步到功能分支：

    ```sh
    git checkout feat-xxx
    git rebase main
    
    # 如果此时有冲突，会弹出解决冲突步骤，依次解决冲突
    ...
    # 解决好后，提交到暂存区
    git add xxx
    # 继续合并
    git rebase --continue
    
    # 合并完成，可以提交到远端仓库。如果rebase影响了远端仓库，需要加-f
    git push
    ```

  * 整理多个提交，改为一个

    ```shell
    # 当前分支往前2个提交，进行rebase；-i代表交互式
    git rebase -i HEAD~2
    # 或
    git rebase -i <commit-ID>
    # 首先会打开一个vim编辑界面，用于选择每个提交的操作。将第2个以下commit前面的`pick`改成`s`。然后保存退出
    ...
    # 会继续打开一个vim界面，用于填写提交的日志。删掉多余信息，按提交规范填日志就行。然后保存退出
    ...
    
    # 可以查看下提交历史
    git log --graph --decorate --all
    
    # 修改完成，可以提交到远端仓库。如果rebase影响了远端仓库，需要加-f
    git push
    ```

* cherry-pick：将执行分支的指定提交合并到当前分支

  比如我在 master 分支提交了某个需求的代码，同时还没提交到远程分支，那么你就可以先 `git log` 查看一下当前的提交，找到 master 分支正常提交之后的所有 commitId，然后复制出来，然后再切到你建好的开发分支，执行cherry-pick：

  ```sh
  git checkout feat-xxx
  # 将多次 commit 变动合并至当前分支
  git cherry-pick <commit-id1> <commit-id2>
  # 将 commit-sha1 到 commit-sha5 中间所有变动合并至当前分支，中间使用..
  git cherry-pick <commit-sha1>..<commit-sha5>
  
  # pick 时解决冲突后继续 pick
  git cherry-pick --continue：
  # 多次 pick 时跳过本次 commit 的 pick 进入下一个 commit 的 pick
  git cherry-pick --skip
  # 完全放弃 pick，恢复 pick 之前的状态
  git cherry-pick --abort
  # 未冲突的 commit 自动变更，冲突的不要，退出这次 pick
  git cherry-pick --quit
  ```

  

