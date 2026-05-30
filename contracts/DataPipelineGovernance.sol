pragma solidity ^0.8.20;

contract DataPipelineGovernance {
    struct Proof {
        string datasetHash;
        string manifestHash;
    }

    mapping(string => Proof) private proofs;

    function storeProof(string memory datasetName, string memory datasetHash, string memory manifestHash) public {
        proofs[datasetName] = Proof(datasetHash, manifestHash);
    }

    function getProof(string memory datasetName) public view returns (string memory, string memory) {
        Proof memory proof = proofs[datasetName];
        return (proof.datasetHash, proof.manifestHash);
    }
}
