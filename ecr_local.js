const AWS = require('aws-sdk');
// import AWS from '/var/runtime/node_modules/aws-sdk/lib/aws.js';

// Configure AWS SDK region
AWS.config.update({ region: 'eu-west-1' }); // Replace with your region

const ecr = new AWS.ECR();
const repositoryNamesToRemove = ["backstage","eight","load-recommendation","actions-runner-dind","openroute-gcc","openroute-eg","openroute-pk","k8s-gh-runner","configuration","demand-modelling-eg-domestic","geofencing","landing","performance","warehouse","transactions-api-test","web","urlshortener"];

// Fetch all images from a repository
async function fetchAllImages(repositoryName, feature) {
  let images = [];
  let nextToken = null;

  do {
    const params = {
      repositoryName: repositoryName,
      filter: { tagStatus: feature },
      nextToken: nextToken
    };

    const response = await ecr.listImages(params).promise();
    images = images.concat(response.imageIds);
    nextToken = response.nextToken;
  } while (nextToken);

  return images;
}

// Get the oldest date of tagged images
async function getOldestDateTagged(repositoryName, images) {
  const pattern = /(master|main|dev)/i;
  const regexFiltered = images.filter(image => pattern.test(image.imageTag));

  if (regexFiltered.length === 0) {
    console.log("regex not found");
    return null;
  } else {
    const imageDetails = await Promise.all(
      regexFiltered.map(image =>
        ecr.describeImages({ repositoryName: repositoryName, imageIds: [image] }).promise()
      )
    );

    const sortedImages = imageDetails
      .map(detail => detail.imageDetails[0])
      .sort((a, b) => new Date(a.imagePushedAt) - new Date(b.imagePushedAt));

    const dateOfOldest = sortedImages[0].imagePushedAt;
    const dateOfNewest = sortedImages[sortedImages.length - 1].imagePushedAt;
    console.log("date of oldest tagged image:", dateOfOldest);
    console.log("date of newest tagged image:", dateOfNewest);

    return dateOfOldest;
  }
}

// Skip images newer than the oldest tagged image
async function skipImageNewerThanOldest(repositoryName, images, dateOfOldest) {
  const imagesDetails = await Promise.all(
    images.map(image =>
      ecr.describeImages({ repositoryName: repositoryName, imageIds: [image] }).promise()
    )
  );

  const imagesFiltered = imagesDetails
    .map(detail => detail.imageDetails[0])
    .filter(detail => new Date(detail.imagePushedAt) < new Date(dateOfOldest));

  return imagesFiltered;
}

// Delete images from a repository
async function deleteImages(repositoryName, imageIds) {
    if (imageIds.length === 0) {
      console.log("No images to delete.");
      return;
    }
    const chunkSize=80;
    for (let i = 0; i < imageIds.length; i += chunkSize) {
    let chunks=imageIds.slice(i, i + chunkSize);
   // console.log(chunks)
    const params = {
    repositoryName: repositoryName,
    imageIds: chunks.map(image => ({ imageDigest: image.imageDigest}))
    }; 
    console.log(params)
      try{
        const response = await ecr.batchDeleteImage(params).promise();
        console.log(response)
        const deletedImages = response.imageIds;
        console.log(`Deleted ${deletedImages.length} images.`);
      } catch (error) {
        console.error(`Error deleting images for repository ${repositoryName}:`, error);
        throw error; // Rethrow the error to propagate it upwards
      } 
    }
  
  
  
  }
async function main() {
//   try {
    const response = await ecr.describeRepositories().promise();
    const allRepoNames = response.repositories
      .map(repo => repo.repositoryName)
      .filter(name => !repositoryNamesToRemove.includes(name));
      let repositoryName="accounts";
    for (const repositoryName of allRepoNames) {
      console.log("working on repo:", repositoryName);

      const imagesUntagged = await fetchAllImages(repositoryName, 'UNTAGGED');
      const imagesTagged = await fetchAllImages(repositoryName, 'TAGGED');

      console.log(`for repository ${repositoryName} total number of tagged images: ${imagesTagged.length}`);
      console.log(`for repository ${repositoryName} total number of untagged images: ${imagesUntagged.length}`);

      if (imagesUntagged.length === 0) {
       continue;
      }

      const dateOfOldest = await getOldestDateTagged(repositoryName, imagesTagged);
      if (!dateOfOldest) {
       continue;
      }

      const imagesToBeDeleted = await skipImageNewerThanOldest(repositoryName, imagesUntagged, dateOfOldest);
      if (imagesToBeDeleted.length === 0) {
        continue;
      }

      console.log(`for repository ${repositoryName} total number of untagged images that will be deleted: ${imagesToBeDeleted.length}`);
    //   console.log(imagesToBeDeleted[0], imagesToBeDeleted[imagesToBeDeleted.length - 1]);
      await deleteImages(repositoryName, imagesToBeDeleted);
    }
// }
}
main().catch(error => console.error(error));
