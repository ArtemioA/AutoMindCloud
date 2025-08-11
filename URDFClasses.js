import * as THREE from 'three';

export class URDFRobot extends THREE.Group {}
export class URDFJoint extends THREE.Group {
    constructor() {
        super();
        this.limit = { lower: -Infinity, upper: Infinity };
        this.mimicJoints = [];
    }
}
export class URDFLink extends THREE.Group {}
export class URDFCollider extends THREE.Group {}
export class URDFVisual extends THREE.Group {}
export class URDFMimicJoint extends URDFJoint {
    constructor() {
        super();
        this.mimicJoint = "";
        this.multiplier = 1.0;
        this.offset = 0.0;
    }
}
