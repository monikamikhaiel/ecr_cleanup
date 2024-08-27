import json
import boto3
import re
from dateutil import parser

# How it works ?
# fetch the images twice one for feature untagged & the other for feture tagged , then get the oldest date of tagged images
# delete the untagged images that are older than that date 
def fetch_all_images(ecr_client,repository_name,feature):
    # list the images in the repository 
    images = []
    next_token = None

    while True:
        if next_token:
            response = ecr_client.list_images(repositoryName=repository_name, nextToken=next_token,filter={'tagStatus': feature})
        else:
            response = ecr_client.list_images(repositoryName=repository_name,filter={'tagStatus': feature})

        images.extend(response['imageIds'])
        if 'nextToken' in response:
            next_token = response['nextToken']
        else:
            break

    return images

def get_oldest_date_tagged(ecr_client,repository_name,images):
    # get the date of tle oldest image with a tag 
    # filter the tags 
    # pattern = re.compile(r'(master|main|dev|staging|production)',re.IGNORECASE)
    pattern = re.compile(r'(master|main|dev)',re.IGNORECASE)
    # print(images)
    regex_filtered= [ s for s in images if pattern.search(s['imageTag']) ]
    if len(regex_filtered)==0 :
        print("regex not found")
        return 0
    else:
        # print(len(images),len(regex_filtered))
        # print(regex_filtered)
        # first one is the oldest
        sorted_images = sorted(regex_filtered, key=lambda x: ecr_client.describe_images(repositoryName=repository_name, imageIds=[x])['imageDetails'][0]['imagePushedAt'], reverse=False)
        oldest_tag=sorted_images[0]['imageTag']
        newest_tag=sorted_images[-1]['imageTag']
        # print("the image with the oldest push date",oldest_tag)
        date_of_oldest=ecr_client.describe_images(repositoryName=repository_name,imageIds=[sorted_images[0]])['imageDetails'][0]['imagePushedAt']
        date_of_newest=ecr_client.describe_images(repositoryName=repository_name, imageIds=[sorted_images[-1]])['imageDetails'][0]['imagePushedAt']
        print("date of oldest image :",date_of_oldest,"tag of oldest image ",oldest_tag)
        print("date of newest image :",date_of_newest,"tag of oldest image ",newest_tag)
        return date_of_oldest
        

def skip_image_newer_than_oldest(ecr_client,repository_name,images,date_of_oldest):
    total_len_untagged=len(images)
    images_filtered = [x for x in images if ecr_client.describe_images(repositoryName=repository_name, imageIds=[x])['imageDetails'][0]['imagePushedAt'] < date_of_oldest]
    sorted_images = sorted(images_filtered, key=lambda x: ecr_client.describe_images(repositoryName=repository_name, imageIds=[x])['imageDetails'][0]['imagePushedAt'], reverse=False)
    length_of_images_to_delete=len(images_filtered)
    return images_filtered
def delete_images(ecr_client,repository_name, image_ids):
    # imageIds=[
    #     {
    #         'imageDigest': 'string',
    #         'imageTag': 'string'
    #     },
    # ]]
    if len(image_ids) == 0:
        print("No images to delete.")
        return
    response = ecr_client.batch_delete_image(repositoryName=repository_name, imageIds=image_ids)
    deleted_images = response['imageIds']
    print(f"Deleted {len(deleted_images)} images.")

    
def lambda_handler(event, context):
    # TODO implement
    ecr_client = boto3.client('ecr')
    response = (ecr_client.describe_repositories(registryId='063605733848'))['repositories']
    ## remove some repos 
    remove_repos=[["REPONAME_TO_BE_EXCLUDED_1","REPONAME_TO_BE_EXCLUDED_2","REPONAME_TO_BE_EXCLUDED_3",........]]
    all_repo_names=[y['repositoryName'] for y in response if y['repositoryName'] not in remove_repos]
    for repository_name in all_repo_names :
    # # repo
    # repository_name="accounts"
        print("working on repo: ",repository_name)
        # get the date of tle oldest image with/without a tag 
        images_untagged = fetch_all_images(ecr_client,repository_name,'UNTAGGED')
        images_tagged = fetch_all_images(ecr_client,repository_name,'TAGGED')
        print ("for repository {} total number of tagged images: ".format(repository_name),len(images_tagged))
        print ("for repository {} total number of untagged images: ".format(repository_name),len(images_untagged))
        if (len(images_untagged)==0): 
            continue
        else: 
            # get the date of tle oldest image with a tag 
            date_of_oldest = get_oldest_date_tagged(ecr_client,repository_name,images_tagged)
            print("date of the oldest tagged image : ",date_of_oldest )
            if (date_of_oldest==0): 
                continue
            else: 
                image_to_be_deleted=skip_image_newer_than_oldest(ecr_client,repository_name,images_untagged,date_of_oldest)
                print ("for repository {} total number of untagged images that will be deleted : ".format(repository_name),len(image_to_be_deleted))
                if (len(image_to_be_deleted)==0): 
                    continue
                else: 
                    print(image_to_be_deleted[0],image_to_be_deleted[-1])
                    # delete_images(ecr_client,repository_name, image_ids)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
