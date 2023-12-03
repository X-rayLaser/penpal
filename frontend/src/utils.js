import React from 'react';

import {
    useLocation,
    useNavigate,
    useParams
} from "react-router-dom";


export const withRouter = WrappedComponent => props => {
    let location = useLocation();
    let navigate = useNavigate();
    let params = useParams();
    return (
        <WrappedComponent
            {...props}
            router={{ location, navigate, params }}
        />
    );
};


export function streamJsonResponse(url, method, data, handleChunk, handleDone) {
    fetch(url, {
        method: method,
        body: JSON.stringify(data),
        headers: {
            "Content-Type": "application/json"
        }
    }).then(response => {
        let reader = response.body.getReader();

        // handle server error
        reader.read().then(function pump({ done, value }) {
            if (done) {
                handleDone();
                return;
            }

            let chunk = new TextDecoder().decode(value);

            handleChunk(chunk);
            
            return reader.read().then(pump);
        });
    });
}
