# intended to run in AWS LAMBDA the code cleanup the old images in a repo in few steps  (for untagged images only )
1. list all repos in account
2. exclude some repos
3. list the images in each repo and sort them by date 
4. find the tagged image with the older date
5. remove all untagged imaged older than the tagged image
